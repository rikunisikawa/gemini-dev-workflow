import boto3
import pandas as pd
import os
import io
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Column names for the mHealth dataset, based on its description
COLUMN_NAMES = [
    'acc_chest_x', 'acc_chest_y', 'acc_chest_z',
    'ecg_lead1', 'ecg_lead2',
    'acc_ankle_x', 'acc_ankle_y', 'acc_ankle_z',
    'gyro_ankle_x', 'gyro_ankle_y', 'gyro_ankle_z',
    'magnet_ankle_x', 'magnet_ankle_y', 'magnet_ankle_z',
    'acc_arm_x', 'acc_arm_y', 'acc_arm_z',
    'gyro_arm_x', 'gyro_arm_y', 'gyro_arm_z',
    'magnet_arm_x', 'magnet_arm_y', 'magnet_arm_z',
    'activity_label'
]

def lambda_handler(event, context):
    """
    Scans for .log files in the S3 raw/ directory, converts them to Parquet,
    and saves them to the stage/ directory.
    """
    s3 = boto3.client('s3')
    bucket = os.environ['BUCKET_NAME']
    
    try:
        # List all .log files in the raw/ directory
        response = s3.list_objects_v2(Bucket=bucket, Prefix='raw/')
        log_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.log')]
        
        if not log_files:
            logger.warning("No .log files found in the raw/ directory. Exiting.")
            return {'statusCode': 200, 'body': 'No new log files to process.'}

        logger.info(f"Found {len(log_files)} log files to process.")

        for log_file_key in log_files:
            logger.info(f"Processing {log_file_key}...")
            
            # Extract user_id from filename, e.g., mHealth_subject1.log -> 1
            user_id_match = re.search(r'subject(\d+)\.log', log_file_key)
            user_id = user_id_match.group(1) if user_id_match else 'unknown'

            # Read the log file from S3
            obj = s3.get_object(Bucket=bucket, Key=log_file_key)
            log_content = obj['Body'].read().decode('utf-8')
            
            # Read into pandas DataFrame
            df = pd.read_csv(io.StringIO(log_content), sep='\t', header=None, names=COLUMN_NAMES)
            
            # Add user_id column
            df['user_id'] = user_id
            
            # Define output key for the stage directory
            parquet_filename = os.path.basename(log_file_key).replace('.log', '.parquet')
            output_key = f'stage/{parquet_filename}'
            
            # Convert DataFrame to Parquet format in-memory
            out_buffer = io.BytesIO()
            df.to_parquet(out_buffer, index=False, engine='pyarrow')
            out_buffer.seek(0)
            
            # Upload Parquet file to S3
            s3.put_object(Bucket=bucket, Key=output_key, Body=out_buffer.read())
            logger.info(f"Successfully converted and uploaded to s3://{bucket}/{output_key}")

        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully processed {len(log_files)} files.')
        }
        
    except Exception as e:
        logger.error(f"An error occurred during Parquet conversion: {e}")
        raise e
