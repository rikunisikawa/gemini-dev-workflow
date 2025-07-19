# mHealth Data Pipeline

This project contains an AWS SAM (Serverless Application Model) application that implements an ETL (Extract, Transform, Load) pipeline for the [mHealth dataset](https://www.kaggle.com/datasets/nirmalsankalana/mhealth-dataset-data-set).

The pipeline automates the process of fetching the dataset from Kaggle, processing it through a series of serverless components, and making it available for analysis in AWS Athena.

## Architecture

The ETL pipeline is orchestrated by **AWS Step Functions** and consists of the following steps:

1.  **Download Data (AWS Lambda)**: A Python Lambda function (`download_and_upload`) is triggered on a schedule. It uses the official Kaggle API to download the mHealth dataset. The raw `.log` files are then uploaded to an S3 bucket under the `raw/` prefix. Kaggle API credentials are securely stored in **AWS Secrets Manager**.

2.  **Convert to Parquet (AWS Lambda)**: A second Python Lambda function (`convert_log_to_parquet`) is invoked. It reads the raw log files from S3, uses the `pandas` library to structure the data, and converts it into the efficient Parquet columnar format. The resulting Parquet files are stored in the `stage/` prefix of the S3 bucket.

3.  **Transform and Catalog (AWS Glue)**: An AWS Glue ETL job runs to perform final transformations on the staged Parquet files. It cleans the data, normalizes the schema (as defined in the target Athena table), and writes the final, analysis-ready data to the `processed/` S3 prefix. The job also updates the **AWS Glue Data Catalog**, creating or updating a table that points to the processed data.

4.  **Scheduled Execution (Amazon EventBridge)**: The entire Step Functions workflow is triggered automatically on a daily schedule by an Amazon EventBridge rule.

5.  **Data Analysis (Amazon Athena)**: Once the pipeline completes, the processed data can be queried interactively using standard SQL through Amazon Athena.

## S3 Bucket Structure

-   `s3://<your-bucket-name>/raw/`: Stores the raw `.log` files downloaded from Kaggle.
-   `s3://<your-bucket-name>/stage/`: Stores the intermediate Parquet files after initial conversion.
-   `s3://<your-bucket-name>/processed/`: Stores the final, transformed Parquet files ready for Athena queries.
-   `s3://<your-bucket-name>/scripts/`: Stores the Glue ETL script.

## Deployment

This application is designed to be built and deployed using the AWS SAM CLI.

### Prerequisites

-   AWS CLI, configured with appropriate credentials.
-   AWS SAM CLI.
-   Docker.
-   An S3 bucket to store the Glue script.
-   An AWS Secrets Manager secret containing your `kaggle.json` credentials.

### Build & Deploy Steps

1.  **Store Kaggle Credentials**:
    Create a secret in AWS Secrets Manager with the contents of your `kaggle.json` file. Note the name of the secret.

2.  **Upload Glue Script to S3**:
    Before deploying, you must upload the Glue ETL script to your S3 bucket.
    ```bash
    aws s3 cp glue/mhealth_etl.py s3://<your-bucket-name>/scripts/mhealth_etl.py
    ```

3.  **Build the SAM Application**:
    This command compiles your Lambda function source code and builds artifacts that can be deployed.
    ```bash
    sam build
    ```

4.  **Deploy the Application**:
    This command packages and deploys your application to AWS. You will be prompted for parameters, such as the bucket name and the name of your Kaggle secret.
    ```bash
    sam deploy --guided
    ```

    Follow the on-screen prompts. When asked for `BucketName`, provide the name of the S3 bucket you are using. For `KaggleSecretName`, provide the name of the secret you created in step 1.

After deployment, the EventBridge rule will be active and will trigger the ETL pipeline on its defined schedule. You can also trigger the Step Functions workflow manually from the AWS Management Console.
