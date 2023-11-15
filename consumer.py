from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType, FloatType, ArrayType
from pyspark.sql.functions import from_json, concat_ws, expr, col, to_date

TOPIC_NAME = 'movies'
SERVER_NAME = 'localhost:9092'

# Create a spark session
spark = SparkSession.builder.appName("KafkaElasticsearchKibana").getOrCreate()

df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "movies") \
    .load()

# Create a schema
schema = StructType([
    StructField('adult', BooleanType(), True),
    StructField('backdrop_path', StringType(), True),
    StructField('genre_ids', ArrayType(IntegerType()), True),
    StructField('id', IntegerType(), True),
    StructField('original_language', StringType(), True),
    StructField('original_title', StringType(), True),
    StructField('overview', StringType(), True),
    StructField('popularity', FloatType(), True),
    StructField('poster_path', StringType(), True),
    StructField('release_date', StringType(), True),
    StructField('title', StringType(), True),
    StructField('video', BooleanType(), True),
    StructField('vote_average', FloatType(), True),
    StructField('vote_count', IntegerType(), True)
])

# Parse the 'value' column
parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json("value", schema).alias("data")) \
    .select("data.*")

# Combine original_title and overview to create a description
parsed_df = parsed_df.withColumn("description", concat_ws(" - ", col("original_title"), col("overview")))

# Normalize popularity and vote_average fields
parsed_df = parsed_df.withColumn("normalized_popularity", expr("popularity / 1000")) \
    .withColumn("normalized_vote_average", expr("vote_average / 10"))

# Convert release_date to DateType
parsed_df = parsed_df.withColumn("release_date", to_date("release_date", "yyyy-MM-dd"))

# Perform further operations or store the data
parsed_df.writeStream.format("console").start().awaitTermination()
