import boto3
import pandas as pd
import os
import io
import json
from pathlib import Path

# Constants
BUCKET_NAME = os.environ.get("BUCKET_NAME")
SOURCE_PREFIX = "raw/"
DESTINATION_PREFIX = "stage/"

# Column names for the mHealth dataset logs
# Based on the dataset description, there are 23 sensor readings + 1 activity label
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

s3_client = boto3.client("s3")

def lambda_handler(event, context):
    """
    Lambda handler to convert .log files from the S3 'raw/' prefix to Parquet
    format in the 'stage/' prefix.
    """
    try:
        print(f"Scanning for .log files in s3://{BUCKET_NAME}/{SOURCE_PREFIX}")
        
        # List all objects in the source prefix
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=SOURCE_PREFIX)
        
        if 'Contents' not in response:
            print("No files found in the source directory. Exiting.")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No new log files to process."})
            }

        log_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.log')]
        
        if not log_files:
            print("No .log files found to process.")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No new log files to process."})
            }

        print(f"Found {len(log_files)} log files to process.")
        processed_files = []

        for s3_key in log_files:
            file_name = Path(s3_key).name
            subject_id = file_name.replace("mHealth_subject", "").replace(".log", "")
            
            print(f"Processing '{s3_key}' for subject '{subject_id}'...")

            # Get the log file object from S3
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            log_content = obj['Body'].read().decode('utf-8')

            # Read the log file into a pandas DataFrame
            # The log files are space-delimited with no header
            df = pd.read_csv(io.StringIO(log_content), header=None, delim_whitespace=True, names=COLUMN_NAMES)
            
            # Add the user_id extracted from the filename
            df['user_id'] = subject_id
            
            # Convert to Parquet format in memory
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            
            # Upload the Parquet file to the stage prefix
            parquet_key = f"{DESTINATION_PREFIX}{file_name.replace('.log', '.parquet')}"
            s3_client.put_object(Bucket=BUCKET_NAME, Key=parquet_key, Body=parquet_buffer.getvalue())
            
            print(f"Successfully converted '{s3_key}' to '{parquet_key}'")
            processed_files.append(parquet_key)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Successfully processed {len(processed_files)} files.",
                "processed_files": processed_files
            })
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        raise e
