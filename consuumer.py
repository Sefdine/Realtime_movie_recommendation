# Import necessary packages
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType, ArrayType, FloatType
from pyspark.sql.functions import from_json, concat_ws, expr, col
from elasticsearch import Elasticsearch
import logging
import sys

# Define a topic name
TOPIC_NAME = 'movies'

print('Connecting to Kafka: ')
try:
    consumer = KafkaConsumer(TOPIC_NAME, bootstrap_servers='localhost:9092')
    print('Connection done !')
except NoBrokersAvailable as ne:
    logging.error('No brokers available: %s', ne)
    sys.exit(1)

# Create a Spark session
spark = SparkSession.builder.appName("ElasticsearchMovies").getOrCreate()

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

# Connect to Elasticsearch
es = Elasticsearch(['localhost:9200'])

# Define the index
index_name = 'movies'

movie_count = 0
for message in consumer:
    # Convert the bytes object to a string
    message_str = message.value.decode('utf-8')
    # Create a dataframe
    df = spark.createDataFrame([message_str], StringType())

    # Parse the JSON data
    parsed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json("value", schema).alias("data")) \
        .select("data.*")
    
    # Combine original_title and overview to create a description
    parsed_df = parsed_df.withColumn("description", concat_ws(" - ", col("original_title"), col("overview")))

    # Normalize popularity and vote_average fields
    parsed_df = parsed_df.withColumn("normalized_popularity", expr("popularity / 1000")) \
        .withColumn("normalized_vote_average", expr("vote_average / 10"))

    try:
        # Convert the Spark DataFrame to a Pandas DataFrame
        pd_df = parsed_df.toPandas()

        # Convert the Pandas DataFrame to a dictionary
        doc = pd_df.to_dict(orient='records')[0]

        # Index the data
        es.index(index=index_name, document=doc)

        print("Data indexed successfully.")
        print(f"Movie {movie_count} inserted !")
        movie_count += 1
    except Exception as e:
        print('Error: ', e)
