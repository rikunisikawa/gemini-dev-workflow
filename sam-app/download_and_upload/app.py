import boto3
import os
import json
import zipfile
from kaggle.api.kaggle_api_extended import KaggleApi
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_kaggle_credentials():
    """Fetches Kaggle API credentials from AWS Secrets Manager."""
    secret_name = os.environ.get("KAGGLE_SECRET_NAME")
    if not secret_name:
        raise ValueError("KAGGLE_SECRET_NAME environment variable not set.")

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        kaggle_credentials = json.loads(secret)
        
        kaggle_config_dir = '/tmp/.kaggle'
        os.makedirs(kaggle_config_dir, exist_ok=True)
        
        with open(f'{kaggle_config_dir}/kaggle.json', 'w') as f:
            json.dump(kaggle_credentials, f)
        os.chmod(f'{kaggle_config_dir}/kaggle.json', 600)
        
        # Set environment variable for Kaggle library
        os.environ['KAGGLE_CONFIG_DIR'] = kaggle_config_dir
        
        logger.info("Successfully configured Kaggle API credentials.")

    except Exception as e:
        logger.error(f"Failed to retrieve Kaggle credentials from Secrets Manager: {e}")
        raise e

def lambda_handler(event, context):
    """
    Downloads the mHealth dataset from Kaggle and uploads log files to S3.
    """
    try:
        get_kaggle_credentials()
        
        api = KaggleApi()
        api.authenticate()

        dataset = 'nirmalsankalana/mhealth-dataset-data-set'
        download_path = '/tmp/mhealth.zip'
        extract_path = '/tmp/mhealth'
        
        logger.info(f"Downloading dataset: {dataset}")
        api.dataset_download_files(dataset, path='/tmp', unzip=False, quiet=False)
        logger.info(f"Successfully downloaded dataset to {download_path}")

        os.makedirs(extract_path, exist_ok=True)
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        logger.info(f"Successfully extracted dataset to {extract_path}")

        s3 = boto3.client('s3')
        bucket = os.environ['BUCKET_NAME']
        
        upload_count = 0
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                if file.endswith(".log"):
                    file_path = os.path.join(root, file)
                    # The log files are inside a subdirectory, e.g., mHealth_subject1.log
                    # We want to keep the original filename in S3.
                    s3_key = f'raw/{file}'
                    logger.info(f"Uploading {file_path} to s3://{bucket}/{s3_key}")
                    s3.upload_file(file_path, bucket, s3_key)
                    upload_count += 1
        
        logger.info(f"Successfully uploaded {upload_count} log files to S3.")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully uploaded {upload_count} files to S3 raw bucket.')
        }

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        # This will cause the Step Functions state to fail
        raise e
