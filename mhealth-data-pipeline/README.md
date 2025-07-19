# mHealth Data Pipeline

This project contains an AWS SAM (Serverless Application Model) application that implements an ETL (Extract, Transform, Load) pipeline for the mHealth dataset from Kaggle.

The pipeline automates the process of fetching the dataset, converting it from log format to Parquet, transforming the data, and making it available for analysis via AWS Athena.

## Architecture

The pipeline is orchestrated by AWS Step Functions and consists of the following main components:

1.  **Lambda Function (`DownloadAndUpload`)**:
    -   Triggered by the Step Functions state machine.
    -   Fetches the mHealth dataset from Kaggle using the official Kaggle API.
    -   Requires Kaggle API credentials (`kaggle.json`) to be stored in AWS Secrets Manager.
    -   Extracts the dataset and uploads the raw `.log` files to `s3://<bucket-name>/raw/`.

2.  **Lambda Function (`ConvertLogToParquet`)**:
    -   Triggered after the download step.
    -   Scans the `raw/` directory for `.log` files.
    -   Uses `pandas` to read the log files, assign column headers, and add the subject ID from the filename.
    -   Converts the data into Parquet format and saves it to `s3://<bucket-name>/stage/`.

3.  **AWS Glue Job (`mhealth-etl-job`)**:
    -   Triggered after the Parquet conversion step.
    -   Reads the staged Parquet files.
    -   Performs transformations:
        -   Maps activity ID numbers to human-readable labels (e.g., `1` -> `Standing`).
        -   Generates a timestamp for each record.
        -   Selects a subset of columns and renames them to match the final schema (`user_id`, `activity`, `timestamp`, `sensor1`, `sensor2`, `sensor3`).
    -   Writes the final, processed data to `s3://<bucket-name>/processed/` in Parquet format, partitioned by `user_id`.
    -   Creates/updates a table in the AWS Glue Data Catalog, making the data queryable by Athena.

4.  **AWS Step Functions (`ETLStateMachine`)**:
    -   Orchestrates the entire workflow in the following order:
        1.  `DownloadAndUpload` Lambda
        2.  `ConvertLogToParquet` Lambda
        3.  `mhealth-etl-job` Glue Job

5.  **Amazon EventBridge Rule (`ScheduledRule`)**:
    -   Triggers the Step Functions state machine on a daily schedule, automating the entire pipeline run.

## Deployment

This application is built and deployed using the AWS SAM CLI.

### Prerequisites

-   AWS SAM CLI
-   Docker
-   AWS CLI, with credentials configured
-   An S3 bucket for SAM to store deployment artifacts.
-   Kaggle API credentials stored in AWS Secrets Manager.

### Steps

1.  **Store Kaggle Credentials**:
    -   Create a new secret in AWS Secrets Manager.
    -   The secret value should be your `kaggle.json` file content, for example: `{"username":"your-username","key":"your-api-key"}`.
    -   Note the name of the secret.

2.  **Build the application**:
    Before deploying, you need to upload the Glue script to your S3 bucket.
    ```bash
    aws s3 cp scripts/glue_etl_job.py s3://<YourBucketName>/scripts/glue_etl_job.py
    ```
    Then, build the SAM application:
    ```bash
    sam build
    ```

3.  **Deploy the application**:
    ```bash
    sam deploy --guided
    ```
    When prompted, provide the following parameters:
    -   `Stack Name`: A name for your CloudFormation stack (e.g., `mhealth-data-pipeline`).
    -   `AWS Region`: The AWS region to deploy to.
    -   `BucketName`: The name of the S3 bucket to be used for the ETL process.
    -   `KaggleSecretName`: The name of the secret you created in step 1.
    -   `GlueJobScriptName`: The name of the glue script in S3 (e.g., `glue_etl_job.py`).
    -   Confirm changes before deploy: `y`

SAM will package the application, upload the artifacts to S3, and deploy the CloudFormation stack.

## Usage

Once deployed, the EventBridge rule will trigger the pipeline automatically on its defined schedule.

You can also manually trigger an execution from the AWS Step Functions console by selecting the `mhealth-etl-statemachine` and starting a new execution.

After a successful run, you can query the processed data in Amazon Athena:

```sql
SELECT * FROM "mhealth_db"."mhealth" WHERE user_id = '1' LIMIT 10;
```
