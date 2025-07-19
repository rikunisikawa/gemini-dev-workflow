import boto3
import os
import json
import zipfile
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# Constants
KAGGLE_SECRET_NAME = os.environ.get("KAGGLE_SECRET_NAME")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
DATASET_ID = 'nirmalsankalana/mhealth-dataset-data-set'
DOWNLOAD_DIR = Path("/tmp/mhealth_download")
EXTRACT_DIR = Path("/tmp/mhealth_extract")
KAGGLE_CONFIG_DIR = Path.home() / ".kaggle"
KAGGLE_JSON_PATH = KAGGLE_CONFIG_DIR / "kaggle.json"

s3_client = boto3.client("s3")
secrets_client = boto3.client("secretsmanager")

def setup_kaggle_credentials():
    """Fetches Kaggle API credentials from Secrets Manager and writes them to the expected location."""
    print("Fetching Kaggle credentials from Secrets Manager...")
    response = secrets_client.get_secret_value(SecretId=KAGGLE_SECRET_NAME)
    secret_string = response['SecretString']
    
    KAGGLE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(KAGGLE_JSON_PATH, 'w') as f:
        f.write(secret_string)
    
    # Set permissions for the kaggle.json file
    os.chmod(KAGGLE_JSON_PATH, 0o600)
    print("Kaggle credentials configured.")

def lambda_handler(event, context):
    """
    Lambda handler to download the mHealth dataset from Kaggle, extract log files,
    and upload them to the 'raw/' prefix in the S3 bucket.
    """
    try:
        # Ensure directories exist and are clean
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

        # Authenticate with Kaggle
        setup_kaggle_credentials()
        api = KaggleApi()
        api.authenticate()
        print("Kaggle API authenticated successfully.")

        # Download dataset
        print(f"Downloading dataset '{DATASET_ID}' to '{DOWNLOAD_DIR}'...")
        api.dataset_download_files(DATASET_ID, path=DOWNLOAD_DIR, unzip=False)
        print("Dataset downloaded.")

        # Unzip the downloaded file
        downloaded_zip = next(DOWNLOAD_DIR.glob("*.zip"))
        print(f"Extracting '{downloaded_zip}' to '{EXTRACT_DIR}'...")
        with zipfile.ZipFile(downloaded_zip, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
        print("Extraction complete.")

        # Upload .log files to S3
        print(f"Uploading .log files to S3 bucket '{BUCKET_NAME}' in 'raw/' prefix...")
        upload_count = 0
        for log_file in EXTRACT_DIR.rglob("*.log"):
            s3_key = f"raw/{log_file.name}"
            print(f"Uploading '{log_file}' to 's3://{BUCKET_NAME}/{s3_key}'")
            s3_client.upload_file(str(log_file), BUCKET_NAME, s3_key)
            upload_count += 1
        
        print(f"Successfully uploaded {upload_count} log files.")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Successfully uploaded {upload_count} log files.",
                "uploaded_files": [f.name for f in EXTRACT_DIR.rglob("*.log")]
            })
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        raise e

