import boto3
import os
import json
import zipfile
from kaggle.api.kaggle_api_extended import KaggleApi

def get_kaggle_credentials(secret_name):
    """Fetches Kaggle API credentials from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        print(f"Error fetching secret: {e}")
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

def lambda_handler(event, context):
    """
    Downloads the mHealth dataset from Kaggle, extracts it, and uploads the log files to S3.
    """
    # --- Configuration ---
    bucket_name = os.environ['BUCKET_NAME']
    secret_name = os.environ['KAGGLE_SECRET_NAME']
    dataset = 'nirmalsankalana/mhealth-dataset-data-set'
    
    # Using /tmp as it's the only writable directory in Lambda
    tmp_dir = '/tmp'
    kaggle_config_dir = os.path.join(tmp_dir, '.kaggle')
    download_path = os.path.join(tmp_dir, 'mhealth')
    zip_file_path = os.path.join(tmp_dir, f"{dataset.split('/')[1]}.zip")

    # --- Authentication ---
    os.makedirs(kaggle_config_dir, exist_ok=True)
    
    credentials = get_kaggle_credentials(secret_name)
    with open(os.path.join(kaggle_config_dir, 'kaggle.json'), 'w') as f:
        json.dump(credentials, f)
    
    os.chmod(os.path.join(kaggle_config_dir, 'kaggle.json'), 600)
    
    # Set environment variable for Kaggle API
    os.environ['KAGGLE_CONFIG_DIR'] = kaggle_config_dir

    api = KaggleApi()
    api.authenticate()

    # --- Download ---
    print(f"Downloading dataset '{dataset}' to '{tmp_dir}'...")
    api.dataset_download_files(dataset, path=tmp_dir, unzip=False)
    print("Download complete.")

    # --- Unzip ---
    os.makedirs(download_path, exist_ok=True)
    print(f"Extracting '{zip_file_path}' to '{download_path}'...")
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(download_path)
    print("Extraction complete.")

    # --- Upload to S3 ---
    s3 = boto3.client('s3')
    uploaded_files = []

    # The extracted files might be in a subdirectory, so we walk the directory tree.
    for root, dirs, files in os.walk(download_path):
        for file in files:
            if file.endswith(".log"):
                local_file_path = os.path.join(root, file)
                s3_key = f'raw/{file}'
                print(f"Uploading '{local_file_path}' to 's3://{bucket_name}/{s3_key}'...")
                s3.upload_file(local_file_path, bucket_name, s3_key)
                uploaded_files.append(s3_key)
    
    print(f"Successfully uploaded {len(uploaded_files)} log files.")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully uploaded {len(uploaded_files)} files.',
            'uploaded_files': uploaded_files
        })
    }
