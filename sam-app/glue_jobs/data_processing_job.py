import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import boto3
from datetime import datetime

# Get job arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'BUCKET_NAME', 'DATABASE_NAME', 'TABLE_NAME'])

# Initialize contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Define S3 paths and catalog info from arguments
bucket_name = args['BUCKET_NAME']
database_name = args['DATABASE_NAME']
table_name = args['TABLE_NAME']

s3_input_path = f"s3://{bucket_name}/stage/"
s3_output_path = f"s3://{bucket_name}/processed/"

# Clean up the processed directory before writing new data to ensure no duplicates
s3 = boto3.resource('s3')
bucket = s3.Bucket(bucket_name)
bucket.objects.filter(Prefix="processed/").delete()

# Create a DynamicFrame from the staged Parquet files
input_dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [s3_input_path], "recurse": True},
    format="parquet",
    transformation_ctx="input_dyf"
)

# --- Transformations ---

# 1. Map fields to match the target Athena schema.
#    - Rename columns to be more user-friendly (snake_case).
#    - Select a subset of columns for the final table.
#    - Add a partition key for the processing date.
# Note: The original dataset does not have a timestamp. We create a 'processing_timestamp'
# to record when the data was processed. The target DDL's 'timestamp' is illustrative.
# The activity_label is an integer, we can map it to a human-readable string if needed.
# For now, we will cast types and rename columns.

# Mapping from old field name to new (type, new_name)
mapping = [
    ("user_id", "string", "user_id", "string"),
    ("activity_label", "long", "activity_id", "int"),
    ("acc_chest_x", "double", "chest_accel_x", "double"),
    ("acc_chest_y", "double", "chest_accel_y", "double"),
    ("acc_chest_z", "double", "chest_accel_z", "double"),
    ("ecg_lead1", "double", "ecg_lead_1", "double"),
    ("ecg_lead2", "double", "ecg_lead_2", "double")
]

mapped_dyf = ApplyMapping.apply(
    frame=input_dyf,
    mappings=mapping,
    transformation_ctx="mapped_dyf"
)

# Add a processing timestamp column
def add_processing_timestamp(rec):
    rec["processing_timestamp"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return rec

timestamped_dyf = Map.apply(frame=mapped_dyf, f=add_processing_timestamp)

# --- Write to S3 and Update Glue Catalog ---

# Define sink to write data to the 'processed' directory and update the catalog
# The catalog update will create the table if it doesn't exist or update its schema.
datasink = glueContext.getSink(
    path=s3_output_path,
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=[], # No partitioning in this example, but could add e.g., ['processing_date']
    enableUpdateCatalog=True,
    transformation_ctx="datasink"
)

datasink.setCatalogInfo(
    catalogDatabase=database_name,
    catalogTableName=table_name
)

datasink.setFormat("parquet")
datasink.writeFrame(timestamped_dyf)

# Commit the job
job.commit()
