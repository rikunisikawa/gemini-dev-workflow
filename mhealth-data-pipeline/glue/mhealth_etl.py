import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, lit, current_timestamp, regexp_replace

# --- Job Initialization ---
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'BUCKET_NAME',
    'SOURCE_PATH',
    'DEST_PATH',
    'DATABASE_NAME',
    'TABLE_NAME'
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# --- Parameters ---
bucket_name = args['BUCKET_NAME']
source_path = args['SOURCE_PATH']
destination_path = args['DEST_PATH']
database_name = args['DATABASE_NAME']
table_name = args['TABLE_NAME']

# --- Read Data from Stage ---
print(f"Reading Parquet data from: {source_path}")
source_dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [source_path], "recurse": True},
    format="parquet"
)

# Convert to Spark DataFrame for easier manipulation
source_df = source_dyf.toDF()

if source_df.rdd.isEmpty():
    print("Source directory is empty. No data to process.")
    job.commit()
    sys.exit(0)

print("Source schema:")
source_df.printSchema()

# --- Transformations ---
# As per the issue's target DDL, we need to select and rename columns.
# DDL: user_id, activity, timestamp, sensor1, sensor2, sensor3
# We will map existing columns to this structure.

# Rename activity_label to activity
transformed_df = source_df.withColumnRenamed("activity_label", "activity")

# Select a subset of sensor columns and rename them for simplicity
# Mapping: acc_chest_x -> sensor1, acc_chest_y -> sensor2, acc_chest_z -> sensor3
transformed_df = transformed_df.select(
    col("user_id"),
    col("activity"),
    col("acc_chest_x").alias("sensor1"),
    col("acc_chest_y").alias("sensor2"),
    col("acc_chest_z").alias("sensor3")
)

# Add a processing timestamp column as requested in the target DDL
transformed_df = transformed_df.withColumn("timestamp", current_timestamp())

print("Transformed schema:")
transformed_df.printSchema()

# --- Write Data to Processed ---
# Convert back to DynamicFrame before writing
output_dyf = DynamicFrame.fromDF(transformed_df, glueContext, "output_dyf")

# Write to S3 in Parquet format, partitioning by user_id for better query performance
print(f"Writing transformed data to: {destination_path}")
glueContext.write_dynamic_frame.from_options(
    frame=output_dyf,
    connection_type="s3",
    connection_options={
        "path": destination_path,
        "partitionKeys": ["user_id"]
    },
    format="parquet"
)

# --- Update Glue Data Catalog ---
print(f"Updating Glue Data Catalog: Database='{database_name}', Table='{table_name}'")
# The sink will automatically create/update the table in the Glue Catalog
s3_sink = glueContext.getSink(
    connection_type="s3",
    path=destination_path,
    enableUpdateCatalog=True,
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=["user_id"],
)
s3_sink.setCatalogInfo(
    catalogDatabase=database_name,
    catalogTableName=table_name
)
s3_sink.setFormat("parquet")
s3_sink.writeFrame(output_dyf)


job.commit()
print("Glue job finished successfully.")
