import os
import flask
import json
from flask import Flask, redirect, url_for, request, render_template
from pymongo import MongoClient

app = Flask(__name__)

mongo_host = os.environ.get('DB_HOST', 'db')
client = MongoClient(mongo_host, 27017)
db = client.classesdb

season = {"Fall": 0, "Winter": 1, "Spring": 2, 0:"Fall", 1:"Winter", 2:"Spring"}


##returns a list of all terms between two specified terms
def date_interval(startdate, enddate):
    words = startdate.split()
    startseason = words[0]
    startyear = int(words[1])
    words = enddate.split()
    endseason = words[0]
    endyear = int(words[1])

    #invalid interval
    if(endyear < startyear):
        return []
    if(endyear == startyear and season[endseason] < season[startseason]):
        return []
    
    returnlist = []

    currentyear = startyear
    currentseason = season[startseason]

    while(True):
        returnlist.append({"TERM_DESC": season[currentseason] + " " + str(currentyear)})

        currentseason += 1

        if(currentseason >= 3):
            currentyear += 1
            currentseason = 0

        if((season[endseason] < currentseason and currentyear == endyear) or currentyear > endyear):
            break

    return returnlist

@app.route("/")
@app.route("/index")
def home():
    app.logger.debug("Main page entry")

    return flask.render_template('index.html')

def get_class_info(subject, number, startdate, enddate):
    dateinterval = date_interval(startdate, enddate)

    results = list(db.classesdb.find({
        "SUBJ": subject,
        "NUMB": number,
        "$or": dateinterval
    }))

    ret = [
        { "professor" : "john smith", "A" : 0.50, "B" : 0.25, "C" : 0.2, "DNF" : 0.05 },
        { "professor" : "jane doe", "A" : 0.05, "B" : 0.20, "C" : 0.25, "DNF" : 0.50 }
        ]

    return json.dumps(ret)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)