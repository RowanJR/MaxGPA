"""
File: app.py

Purpose:
Runs the Flask backend for MaxGPA and provides API endpoints that return
course grade distribution data from MongoDB.

System Context:
This file is part of the MaxGPA system. It connects the frontend (index.html
and app.js) to the MongoDB database populated by import_csv.py. It processes
requests for course data and returns formatted grade distributions.

Authors:
- Rowan Moore
- Hayden Oelke
- Caeleb Renner
- Jake Seiberg

Date Created:
04/16/2026

Modifications:
- 04/23/2026: Added course query and aggregation logic.
- 04/29/2026: Integrated API endpoint and improved data handling.
- 04/30/2026: Added support for course numbers with Z suffix and improved formatting.
- 05/02/2026: Added admin CSV upload endpoint.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os        # Used to read environment variables
import io        # Used to wrap uploaded file bytes for pandas
import json      # Used to load degree requirements from JSON file
import pandas as pd  # Used to parse uploaded CSV data
from flask import Flask, request, render_template, jsonify  # Web framework
from pymongo import MongoClient  # MongoDB connection

# Import shared data-cleaning helpers from the import pipeline
from import_csv import clean_value, has_real_grade_data


# ---------------------------------------------------------------------
# App and Database Setup
# ---------------------------------------------------------------------

app = Flask(__name__)  # flask application instance
mongo_host = os.environ.get('DB_HOST', 'db')  # MongoDB host from environment or default
client = MongoClient(mongo_host, 27017)  # MongoDB client connection
db = client.maxgpa  # reference to the maxgpa database

# ---------------------------------------------------------------------
# Static Configuration Data
# ---------------------------------------------------------------------

# MAJOR_MAP is used to map the shortened major codes sent from the frontend 
# javascript to full names for database querying
MAJOR_MAP = {
    "cs_bs":       "Bachelor of Science in Computer Science",
    "bs_business": "Bachelor of Science in Business Administration",
    "phys_bs":     "Bachelor of Science in Physics",
}

with open("degree_requirements.json") as f:  # file handle for degree requirements JSON
    _degree_data = json.load(f)  # parsed degree requirements data from JSON file

# List of all degrees with all their courses. Generated from 
# "degree_requirements.json" on startup
DEGREES = {d["name"]: d["courses"] for d in _degree_data["degrees"]}


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def ay_to_terms(year_from, year_to):
    """
    converts acedmeic "year_from" and "year_to" into a list of eact terms to be searched in the database
    terms are formatted "Fall 2016"
    """
    terms = set()  # Final list of all terms to be returned
    for ay in range(int(year_from), int(year_to) + 1):
        terms.add(f"Fall {ay}")
        terms.add(f"Winter {ay + 1}")
        terms.add(f"Spring {ay + 1}")
    return terms


def to_pct(counts):
    """
    converts a list of integers representing grades acquired for a certain course into percentages
    """
    total = sum(counts.values())  # Total number of grades to be used in finding average
    if total == 0:
        return {"A": 0, "B": 0, "C": 0, "DNF": 0}
    return {k: round(v / total * 100, 1) for k, v in counts.items()}


def get_class_info(subj, numb, valid_terms):
    """
    queries the database to find a specific class during a set of terms and returns 
    the average grades for each professor who has taught that course at least once
    during that period as a list of dictionaries containing the instructor "name" key
    and the grades as a percentage in an array with the "grades" key
    """
    numb = str(numb).strip()  # class number
    number_options = {numb}  # set of possible course number variations
    if numb.endswith("Z"):
        number_options.add(numb[:-1])
    else:
        number_options.add(numb + "Z")

    ## make a results list that contains all individual classes taught during the valid terms
    results = list(db.course_grades.find({
        "SUBJ": subj,
        "NUMB": {"$in": list(number_options)},
        "TERM_DESC": {"$in": list(valid_terms)}
    }))

    if not results:
        return []

    per_inst = {}  # dictionary mapping instructor names to their grade counts
    all_totals = {"A": 0, "B": 0, "C": 0, "DNF": 0}  # grade counts across all instructors

    for row in results:
        inst = str(row.get("INSTRUCTOR", "Unknown")).strip()  # instructor name from the course record
        if not inst:
            inst = "Unknown"
        if inst not in per_inst:
            per_inst[inst] = {"A": 0, "B": 0, "C": 0, "DNF": 0}

        a   = int(row.get("AP", 0)) + int(row.get("A", 0)) + int(row.get("AM", 0))  # total A grades
        b   = int(row.get("BP", 0)) + int(row.get("B", 0)) + int(row.get("BM", 0))  # total B grades
        c   = int(row.get("CP", 0)) + int(row.get("C", 0)) + int(row.get("CM", 0))  # total C grades
        dnf = int(row.get("DP", 0)) + int(row.get("D", 0)) + int(row.get("DM", 0)) + int(row.get("F", 0))  # total DNF grades 

        per_inst[inst]["A"]   += a
        per_inst[inst]["B"]   += b
        per_inst[inst]["C"]   += c
        per_inst[inst]["DNF"] += dnf
        all_totals["A"]   += a
        all_totals["B"]   += b
        all_totals["C"]   += c
        all_totals["DNF"] += dnf

    instructors = [{"name": "All Instructors", "grades": to_pct(all_totals)}]  # list starting with all instructor data as percentages
    for name, counts in sorted(per_inst.items(), key=lambda x: x[1]["A"], reverse=True):
        instructors.append({"name": name, "grades": to_pct(counts)})

    return instructors


def resolve_course(entry, valid_terms):
    """
    calls "get_class_info" and returns a formatted dict containing the
    class code, title, credits, and list of instructors from get_class_info,
    each with a "name" key and "grade" key with a list of grades
    """
    if "or" in entry:
        for option in entry["or"]:
            subj, numb = option["code"].split()  # Subject and course number from course code
            instructors = get_class_info(subj, numb, valid_terms)  # Grade data for this course option
            if instructors:
                return {
                    "code": option["code"],
                    "title": option["title"],
                    "credits": entry.get("credits", 4),
                    "instructors": instructors,
                }
        opt = entry["or"][0]  # First alternative course option
        return {
            "code": opt["code"],
            "title": opt["title"],
            "credits": entry.get("credits", 4),
            "instructors": [],
        }
    else:
        subj, numb = entry["code"].split()  # subject and course number from course code
        return {
            "code": entry["code"],
            "title": entry["title"],
            "credits": entry.get("credits", 4),
            "instructors": get_class_info(subj, numb, valid_terms),
        }


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@app.route("/")
@app.route("/index")
def home():
    """
    returns the default page when accessed in a web browser
    """
    return render_template("index.html")


@app.route("/api/years")
def api_years():
    """
    returns a json list of all years currently present in the database to
    be presented as options to the user
    """
    term_descs = db.course_grades.distinct("TERM_DESC")  # all unique term descriptions in the database

    ay_set = set()  # all academic years found in the database

    for term in term_descs:
        parts = str(term).strip().split()  # term season and year components
        if len(parts) != 2:
            continue

        season, year_str = parts[0], parts[1]  # season (Fall/Winter/Spring) and year string

        try:
            cal_year = int(year_str)  # calendar year
        except ValueError:
            continue

        # Fall YYYY belongs to AY starting YYYY
        # Winter/Spring YYYY belong to AY that started YYYY-1
        if season == "Fall":
            ay_set.add(cal_year)
        elif season in ("Winter", "Spring"):
            ay_set.add(cal_year - 1)

    return jsonify({"years": sorted(ay_set)})


@app.route("/api/grades")
def api_grades():
    """
    Requires parameters for major, year_from, and year_to. Searches the database for 
    each class in the major to find the grade data for instructors. returns a json
    with all courses present, with each course having a "code", "title", "credits", 
    and "instructors" key, where instructors is a list of instructors, each with a 
    "name" key and "grades" key, containing a list of grade data as percentages
    """
    major_key = request.args.get("major", "")
    year_from = request.args.get("year_from", "2016")
    year_to   = request.args.get("year_to", "2023")

    major_name = MAJOR_MAP.get(major_key)  # full major name
    if not major_name or major_name not in DEGREES:
        return jsonify({"error": "Unknown major"}), 400

    valid_terms = ay_to_terms(year_from, year_to)  # set of all valid terms for the requested years
    courses = [resolve_course(e, valid_terms) for e in DEGREES[major_name]]  # list of course details for the major

    return jsonify({
        "major": major_name,
        "years": f"AY{year_from}–AY{year_to}",
        "terms": [
            {
                "year": "Degree Sequence",
                "term": "Required Courses",
                "courses": courses,
            }
        ],
    })


@app.route("/api/admin/upload-csv", methods=["POST"])
def admin_upload_csv():
    """
    Accept a CSV file upload from the admin panel and import its records
    into MongoDB. Uses clean_value and has_real_grade_data from import_csv.py
    to keep data cleaning consistent with the main import pipeline.
    Deduplicates against existing data before inserting.
    """

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]  # uploaded file

    if not file.filename or not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "File must be a .csv"}), 400

    try:
        content = file.read()  # uploaded file
        df = pd.read_csv(io.BytesIO(content), dtype={"NUMB": str})  # parsed CSV as a DataFrame
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {str(e)}"}), 422

    # Reuse import_csv.py cleaning logic
    df = df[df.apply(has_real_grade_data, axis=1)]
    df = df.apply(lambda col: col.map(clean_value))

    new_docs = df.to_dict(orient="records")  # list of dictionaries

    if not new_docs:
        return jsonify({"error": "CSV contained no valid grade rows."}), 422

    collection = db.course_grades  # reference to the course_grades collection in MongoDB

    # Deduplicate against existing records
    def fingerprint(doc):
        return (
            str(doc.get("SUBJ", "")).strip(),
            str(doc.get("NUMB", "")).strip(),
            str(doc.get("TERM_DESC", "")).strip(),
            str(doc.get("INSTRUCTOR", "")).strip(),
        )

    existing_fps = set(  # set of fingerprints from all existing database records
        fingerprint(doc)
        for doc in collection.find(
            {}, {"SUBJ": 1, "NUMB": 1, "TERM_DESC": 1, "INSTRUCTOR": 1, "_id": 0}
        )
    )

    to_insert = [d for d in new_docs if fingerprint(d) not in existing_fps]  # records that are not already in the database
    duplicates_removed = len(new_docs) - len(to_insert)  # count of duplicate records filtered out

    if to_insert:
        collection.insert_many(to_insert)

    return jsonify({
        "filename": file.filename,
        "rows_imported": len(to_insert),
        "duplicates_removed": duplicates_removed,
    }), 200


# ---------------------------------------------------------------------
# Program Entry Point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)