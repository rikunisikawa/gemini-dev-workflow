import os
import pandas as pd
import boto3
import re

# Define the column names for the mHealth dataset
COLUMN_NAMES = [
    'acc_chest_x', 'acc_chest_y', 'acc_chest_z',
    'ecg_lead1', 'ecg_lead2',
    'acc_ankle_x', 'acc_ankle_y', 'acc_ankle_z',
    'gyro_ankle_x', 'gyro_ankle_y', 'gyro_ankle_z',
    'mag_ankle_x', 'mag_ankle_y', 'mag_ankle_z',
    'acc_wrist_x', 'acc_wrist_y', 'acc_wrist_z',
    'gyro_wrist_x', 'gyro_wrist_y', 'gyro_wrist_z',
    'mag_wrist_x', 'mag_wrist_y', 'mag_wrist_z',
    'activity_label'
]

def lambda_handler(event, context):
    """
    Scans for .log files in the S3 'raw/' prefix, converts them to Parquet,
    and saves them to the 'stage/' prefix.
    """
    bucket_name = os.environ['BUCKET_NAME']
    raw_prefix = 'raw/'
    stage_prefix = 'stage/'

    s3 = boto3.client('s3')
    
    # List all .log files in the raw directory
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=raw_prefix)
        log_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.log')]
    except Exception as e:
        print(f"Error listing files in s3://{bucket_name}/{raw_prefix}: {e}")
        raise e

    if not log_files:
        print("No log files found to process.")
        return {
            'statusCode': 200,
            'body': 'No log files found to process.'
        }

    print(f"Found {len(log_files)} log files to process.")
    processed_files = []

    for log_file_key in log_files:
        try:
            file_name = os.path.basename(log_file_key)
            s3_path = f"s3://{bucket_name}/{log_file_key}"
            
            print(f"Processing {s3_path}...")

            # Read the space-delimited log file into a pandas DataFrame
            df = pd.read_csv(s3_path, sep='\s+', header=None, names=COLUMN_NAMES, engine='python')

            # Extract subject ID from the filename (e.g., mHealth_subject1.log -> 1)
            match = re.search(r'subject(\d+)', file_name)
            if match:
                subject_id = int(match.group(1))
                df['subject_id'] = subject_id
            else:
                df['subject_id'] = -1 # Default value if not found

            # Convert to Parquet and save to the stage directory
            parquet_file_name = file_name.replace('.log', '.parquet')
            parquet_s3_path = f"s3://{bucket_name}/{stage_prefix}{parquet_file_name}"
            
            print(f"Writing Parquet file to {parquet_s3_path}...")
            df.to_parquet(parquet_s3_path, engine='pyarrow', index=False)
            processed_files.append(parquet_s3_path)

        except Exception as e:
            print(f"Error processing file {log_file_key}: {e}")
            # Continue to next file
            continue

    print(f"Successfully processed {len(processed_files)} files.")
    return {
        'statusCode': 200,
        'body': {
            'message': f'Successfully processed {len(processed_files)} files.',
            'processed_files': processed_files
        }
    }
