import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, when, lit, row_number, current_timestamp
from pyspark.sql.window import Window
from pyspark.sql.types import TimestampType

# --- Job Initialization ---
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'S3_SOURCE_PATH',
    'S3_TARGET_PATH',
    'CATALOG_DATABASE_NAME',
    'CATALOG_TABLE_NAME'
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# --- Parameters ---
s3_source_path = args['S3_SOURCE_PATH']
s3_target_path = args['S3_TARGET_PATH']
db_name = args['CATALOG_DATABASE_NAME']
table_name = args['CATALOG_TABLE_NAME']

# --- Read Data ---
# Read Parquet data from the stage directory
datasource = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [s3_source_path], "recurse": True},
    format="parquet"
)

df = datasource.toDF()

if df.rdd.isEmpty():
    print("No data to process. Exiting job.")
    job.commit()
    sys.exit(0)

# --- Transformations ---

# 1. Map activity labels to meaningful names
activity_mapping = {
    0: 'Null', 1: 'Standing', 2: 'Sitting', 3: 'Lying', 4: 'Walking',
    5: 'Walking_Upstairs', 6: 'Walking_Downstairs', 7: 'Standing_in_Elevator',
    8: 'Moving_in_Elevator', 9: 'Walking_in_Parking_Lot',
    10: 'Walking_on_Treadmill', 11: 'Running_on_Treadmill', 12: 'Climbing_Stairs'
}
mapping_expr = when(col("activity_label").isNull(), None)
for key, value in activity_mapping.items():
    mapping_expr = mapping_expr.when(col("activity_label") == key, value)
df = df.withColumn("activity", mapping_expr.otherwise("Unknown"))

# 2. Generate timestamp (assuming 50Hz sample rate)
# Create a sequence number for each subject's readings
window_spec = Window.partitionBy("subject_id").orderBy(lit(1)) # Order is not guaranteed, but we need a sequence
df = df.withColumn("sequence_num", row_number().over(window_spec))

# Generate timestamp by adding sequence number * 20ms (for 50Hz) to a base timestamp
df = df.withColumn("generated_timestamp", (current_timestamp().cast("long") + col("sequence_num") * 0.02).cast(TimestampType()))


# 3. Select and rename columns to match the target Athena DDL
final_df = df.select(
    col("subject_id").alias("user_id").cast("string"),
    col("activity"),
    col("generated_timestamp").alias("timestamp"),
    col("acc_chest_x").alias("sensor1").cast("double"),
    col("acc_chest_y").alias("sensor2").cast("double"),
    col("acc_chest_z").alias("sensor3").cast("double")
)

# --- Write Data ---
# Convert back to DynamicFrame
dynamic_frame_to_write = DynamicFrame.fromDF(final_df, glueContext, "dynamic_frame_to_write")

# Write the transformed data to the processed S3 path, partitioned by user_id
# This also creates/updates the table in the Glue Data Catalog
glueContext.write_dynamic_frame.from_options(
    frame=dynamic_frame_to_write,
    connection_type="s3",
    connection_options={
        "path": s3_target_path,
        "database": db_name,
        "table": table_name,
        "partitionKeys": ["user_id"]
    },
    format="parquet",
    transformation_ctx="datasink"
)

job.commit()
