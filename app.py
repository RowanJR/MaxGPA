import os
import flask
from flask import Flask, redirect, url_for, request, render_template
from pymongo import MongoClient

app = Flask(__name__)

mongo_host = os.environ.get('DB_HOST', 'db')
client = MongoClient(mongo_host, 27017)
db = client.timesdb

@app.route("/")
@app.route("/index")
def home():
    _items = db.timesdb.find()
    items = [item for item in _items]
    app.logger.debug("Main page entry")

    return flask.render_template('calc.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)