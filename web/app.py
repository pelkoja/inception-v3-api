from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json
import numpy
import tensorflow

app = Flask(__name__)
api = Api(app)

client = MongoClient('mongodb://db:27017')
db = client.image_recognition
users = db['Users']

def user_exists(username):
    if users.find({'Username': username}).count() == 0:
        return False
    else:
        return True

class Register(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data['username']
        password = posted_data['password']

        if user_exists(username):
            ret_json = {
                'status': 301,
                'message': 'Invalid username'
            }
            return jsonify(ret_json)

        hashed_password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            'Username': username,
            'Password': hashed_password,
            'Tokens': 4
        })

        ret_json = {
            'status': 200,
            'message': 'Succesfully signed'
        }
        return jsonify(ret_json)

def verify_password(username, password):
    if not user_exists(username):
        return False

    hashed_password = users.find({
        'Username': username
    })[0]['Password']

    if bcrypt.hashpw(password.encode('utf8'), hashed_password) == hashed_password:
        return True
    else:
        return False

def generate_return_dict(status, message):
    ret_json = {
        'status': status,
        'message': message
    }
    return ret_json

def verify_credentials(username, password):
    if not user_exists(username):
        return generate_return_dict(301, 'Invalid username'), True

    correct_password = verify_password(username, password)
    if not correct_password:
        return generate_return_dict(302, 'Invalid password'), True

    return None, False


class Classify(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data['username']
        password = posted_data['password']
        url = posted_data['url']

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        tokens = users.find({
            'Username': username
        })[0]['Tokens']

        if tokens <= 0:
            return jsonify(generate_return_dict(303, 'Not enough tokens!'))

        r = requests.get(url)
        ret_json = {}

        with open('temp.jpg', 'wb') as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            ret = proc.communicate()[0]
            proc.wait()
            with open('text.txt') as g:
                ret_json = json.load(g)

        users.update({
            'Username': username
        },{
            '$set':{
                'Tokens': tokens - 1
            }
        })
        return ret_json

class Refill(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data['username']
        password = posted_data['admin_password']
        amount = posted_data['amount']

        if not user_exists(username):
            return jsonify(generate_return_dict(301, 'Invalid username'))

        correct_password = "abc123"

        if not password == correct_password:
            return jsonify(generate_return_dict(304, 'Invalid admin password'))

        users.update({
            'Username': username
        },{
            '$set':{
                'Tokens': amount
            }
        })
        return jsonify(generate_return_dict(200, 'Refilled succesfully'))

api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
