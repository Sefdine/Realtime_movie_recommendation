import requests
import json
import sys
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import logging

# Set up logging
logging.basicConfig(level=logging.ERROR)

# Define the topic name and the bootstrap server
TOPIC = 'movies'
SERVER_NAME = 'localhost:9092'

# Initialize kafka producer
print('Connecting to Kafka')
try:
    producer = KafkaProducer(bootstrap_servers=SERVER_NAME, value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    print('Connection done !')
except NoBrokersAvailable as ne:
    logging.error('No brokers available: %s', ne)
    sys.exit(1)

API_KEY = 'd8bcb8f65f58af4646d3ecaab13be613'
MOVIE_ENDPOINT = "https://api.themoviedb.org/3/movie/popular?page={}"

params = {
    'api_key': API_KEY,
    'language': 'en-US'
}

complete_movies = []

for i in range (1, 501):
    try:
        response = requests.get(MOVIE_ENDPOINT.format(500), params=params)

        if response.status_code == 200:
            movies = response.json()['results']
            producer.send(TOPIC, value=movies)
            producer.flush()

            print(f"Movie n°{len(complete_movies)+1} sent successfully!", end='\r')
            complete_movies.extend(movies)
        else:
            print("Error fetching data from TMDb API")
    except NoBrokersAvailable as ne:
        logging.error('No brokers available: %s', ne)
        break

    except Exception as e:
        logging.error('Error: %s', e)

print(len(complete_movies))
producer.close()