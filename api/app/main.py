from elasticsearch import Elasticsearch
from flask import Flask,jsonify,url_for,redirect,render_template,request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from math import ceil
import secrets

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = secrets.token_hex(16)

# create connection with elasticsearch version
client = Elasticsearch(
    "http://localhost:9200",
    )

index_name = 'movies'

# Get all movies
def get_all_movies():
    query = {
        "query": {
             "match_all": {}
        }
    }
    result = client.search(index=index_name, body=query)
    total_movies = result['hits']['total']['value']
    return total_movies

# Get 10 movies
@app.route('/api/movies/<string:movie_id>', methods=['GET'])
def get_movies(page=1, size=12):
    page = 1 if page <= 0 else page
    query = {
        "query": {
            "match_all": {}
        },
        "from": (page - 1) * size,
        "size": size
    }
    result = client.search(index=index_name, body=query)
    return result['hits']['hits']

def get_similar_movies(title):

    # Query to find a movie by title
    query = {
        "query": {
            "match": {
                "title": title
            }
        }
    }

    response = client.search(index='movies', body=query)

    # Extract movie information
    if response['hits']['total']['value'] > 0 :
        movie_info = response['hits']['hits'][0]['_source']
        movie_info['vote_average'] = round(movie_info['vote_average'], 2)
        # remove the field not used      
        del movie_info["adult"]
        del movie_info["backdrop_path"]
        del movie_info["original_title"]
        del movie_info["video"]
        del movie_info["description"]

        # Query to find similar movies
        recommendation_query = {
            "query": {
                "bool": {
                    "must_not": [
                        {"match": {"title": title}}
                    ],

                    "filter": [
                        {"terms": {"genre_ids": movie_info.get('genre_ids', [])}},
                        {"range": {"vote_average": {"gte": movie_info.get('vote_average', 0)}}},
                        {"range": {"popularity": {"gte": movie_info.get('popularity', 0)}}}
                    ]
                }
            },
        }

        recommendation_response = client.search(index='movies', body=recommendation_query,size=5)

        Movies = []
        # Extract movie recommendations
        recommendations = [hit['_source'] for hit in recommendation_response['hits']['hits']]

        for movie in recommendations :
            movie['vote_average'] = round(movie['vote_average'], 2)
            del movie["adult"]
            del movie["genre_ids"]
            del movie["backdrop_path"]
            del movie["original_title"]
            del movie["video"]
            del movie["description"]
            # del movie["poster_path"]
            Movies.append(movie)

        return {'movie_getted': movie_info,'recommendations': Movies}
    else:
        return None

class MovieForm(FlaskForm):
    movie_name = StringField('Movie Name', validators=[DataRequired()])
    submit = SubmitField('Recommand me')

@app.route('/movie/<string:title>')
def get_movie_info(title):
    result = get_similar_movies(title)
    if result:
        return jsonify(result)
    else:
        return jsonify({'title': title, 'message': 'Movie not found'})

@app.route('/', methods=['GET', 'POST'])
def index():
    page = int(request.args.get('page', 1))
    if(page <= 0):
       page = 1
    size = int(request.args.get('size', 12))
    movies = get_movies(page,size)
    total_movies = get_all_movies()
    total_pages = ceil(total_movies / size)

    form = MovieForm()
    result = None

    if form.validate_on_submit():
        movie_name = form.movie_name.data
        result = get_similar_movies(movie_name)

    return render_template("index.html",form=form, movies=movies, page=page, size=size, total_pages=total_pages, result=result)    

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=9090,
        debug=True
    )