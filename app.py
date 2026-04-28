import os
import flask
import json
from flask import Flask, redirect, url_for, request, render_template
from pymongo import MongoClient

app = Flask(__name__)

mongo_host = os.environ.get('DB_HOST', 'db')
client = MongoClient(mongo_host, 27017)
db = client.maxgpa

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

@app.route("/get_class_list")
def get_class_list():

    startdate = "Winter 2015"
    enddate = "Spring 2018"

    ret = {
        "PHYS 101" : get_class_info("PHYS", 101, startdate, enddate), 
        "MATH 101" : get_class_info("MATH", 101, startdate, enddate)
    }

    return flask.jsonify(ret)

def get_class_info(subject, number, startdate, enddate):
    dateinterval = date_interval(startdate, enddate)

    results = list(db.maxgpa.find({
        "SUBJ": subject,
        "NUMB": number,
        "$or": dateinterval
    }))

    intermed_professors = {}

    for result in results:
        if result["INSTRUCTOR"] not in intermed_professors:
            intermed_professors[result["INSTRUCTOR"]] = {"A" : 0, "B" : 0, "C" : 0, "DNF" : 0}
        
        intermed_professors[result["INSTRUCTOR"]]["A"] += int(result["A"])
        intermed_professors[result["INSTRUCTOR"]]["A"] += int(result["AP"])
        intermed_professors[result["INSTRUCTOR"]]["A"] += int(result["AM"])
        intermed_professors[result["INSTRUCTOR"]]["B"] += int(result["B"])
        intermed_professors[result["INSTRUCTOR"]]["B"] += int(result["BP"])
        intermed_professors[result["INSTRUCTOR"]]["B"] += int(result["BM"])
        intermed_professors[result["INSTRUCTOR"]]["C"] += int(result["C"])
        intermed_professors[result["INSTRUCTOR"]]["C"] += int(result["CP"])
        intermed_professors[result["INSTRUCTOR"]]["C"] += int(result["CM"])
        intermed_professors[result["INSTRUCTOR"]]["DNF"] += int(result["D"])
        intermed_professors[result["INSTRUCTOR"]]["DNF"] += int(result["DP"])
        intermed_professors[result["INSTRUCTOR"]]["DNF"] += int(result["DM"])
        intermed_professors[result["INSTRUCTOR"]]["DNF"] += int(result["F"])

    for professor in intermed_professors:
        pass

    ret = [
        { "professor" : "john smith", "A" : 0.50, "B" : 0.25, "C" : 0.2, "DNF" : 0.05 },
        { "professor" : "jane doe", "A" : 0.05, "B" : 0.20, "C" : 0.25, "DNF" : 0.50 }
    ]

    return flask.jsonify(ret)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)