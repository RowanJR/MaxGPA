import os
import flask
from flask import Flask, redirect, url_for, request, render_template
from pymongo import MongoClient

app = Flask(__name__)

mongo_host = os.environ.get('DB_HOST', 'db')
client = MongoClient(mongo_host, 27017)
db = client.classesdb

@app.route("/")
@app.route("/index")
def home():
    app.logger.debug("Main page entry")

    return flask.render_template('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)