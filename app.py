"""
File: app.py

Purpose:
Runs the Flask backend for MaxGPA and provides API routes that return course
grade distribution data from MongoDB.

System Context:
This file is part of the MaxGPA system. MaxGPA is a Flask and MongoDB web
application that helps users compare grade distributions for required courses
in selected degree programs. This file connects the frontend to the MongoDB
course grade database and formats course/instructor grade data as JSON.

Authors:
- Rowan Moore
- Hayden Oelke
- Caeleb Renner

Date Created:
04/16/2026

Modifications:
- 04/16/2026: Initial Flask server setup and routing.
- 04/23/2026: Added course data retrieval logic.
- 04/28/2026: Backend improvements.
- 04/29/2026: Integrated API endpoint and improved data pipeline.
- 04/30/2026: Refactored backend to support updated CSV structure.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os      # Used to access environment variables
import json    # Used to load degree requirement data
from flask import Flask, request, render_template, jsonify  # Web framework
from pymongo import MongoClient  # MongoDB connection


# ---------------------------------------------------------------------
# App and Database Initialization
# ---------------------------------------------------------------------

app = Flask(__name__)  
# Flask application instance

mongo_host = os.environ.get('DB_HOST', 'db')  
# Database host (defaults to "db" for Docker)

client = MongoClient(mongo_host, 27017)  
# MongoDB client connection

db = client.maxgpa  
# Reference to the "maxgpa" database


# ---------------------------------------------------------------------
# Static Configuration Data
# ---------------------------------------------------------------------

MAJOR_MAP = {
    "cs_bs":       "Bachelor of Science in Computer Science",
    "bs_business": "Bachelor of Science in Business Administration",
    "geog_bs":     "Bachelor of Science in Physics",
}
# Maps frontend keys to full degree names

with open("degree_requirements.json") as f:
    _degree_data = json.load(f)  
# Raw degree requirement data loaded from JSON

DEGREES = {d["name"]: d["courses"] for d in _degree_data["degrees"]}  
# Dictionary mapping degree name to list of courses


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def ay_to_terms(year_from, year_to):
    """
    Convert academic year range into a set of term strings.
    """

    terms = set()  
    # Set to store valid terms

    # Loop through each academic year
    for ay in range(int(year_from), int(year_to) + 1):
        terms.add(f"Fall {ay}")
        terms.add(f"Winter {ay + 1}")
        terms.add(f"Spring {ay + 1}")

    return terms


def to_pct(counts):
    """
    Convert grade counts into percentages.
    """

    total = sum(counts.values())  
    # Total number of grades

    # If no grades exist, return zeros
    if total == 0:
        return {"A": 0, "B": 0, "C": 0, "DNF": 0}

    # Convert each grade count into percentage
    return {k: round(v / total * 100, 1) for k, v in counts.items()}


def get_class_info(subj, numb, valid_terms):
    """
    Query MongoDB and return instructor grade distributions.
    """

    numb = str(numb).strip()  
    # Normalize course number

    number_options = {numb}  
    # Set of possible course number variations

    # Add alternative format (with or without Z)
    if numb.endswith("Z"):
        number_options.add(numb[:-1])
    else:
        number_options.add(numb + "Z")

    # Query MongoDB for matching courses
    results = list(db.course_grades.find({
        "SUBJ": subj,
        "NUMB": {"$in": list(number_options)},
        "TERM_DESC": {"$in": list(valid_terms)}
    }))

    # If no results found, return empty list
    if not results:
        return []

    per_inst = {}  
    # Dictionary storing grade totals per instructor

    all_totals = {"A": 0, "B": 0, "C": 0, "DNF": 0}  
    # Aggregate totals across all instructors

    # Process each row from database
    for row in results:
        inst = str(row.get("INSTRUCTOR", "Unknown")).strip() or "Unknown"

        # Initialize instructor entry if not present
        if inst not in per_inst:
            per_inst[inst] = {"A": 0, "B": 0, "C": 0, "DNF": 0}

        # Calculate grade group totals
        a   = int(row.get("AP", 0)) + int(row.get("A", 0)) + int(row.get("AM", 0))
        b   = int(row.get("BP", 0)) + int(row.get("B", 0)) + int(row.get("BM", 0))
        c   = int(row.get("CP", 0)) + int(row.get("C", 0)) + int(row.get("CM", 0))
        dnf = int(row.get("DP", 0)) + int(row.get("D", 0)) + int(row.get("DM", 0)) + int(row.get("F", 0))

        # Update instructor totals
        per_inst[inst]["A"] += a
        per_inst[inst]["B"] += b
        per_inst[inst]["C"] += c
        per_inst[inst]["DNF"] += dnf

        # Update global totals
        all_totals["A"] += a
        all_totals["B"] += b
        all_totals["C"] += c
        all_totals["DNF"] += dnf

    instructors = [{"name": "All Instructors", "grades": to_pct(all_totals)}]
    # List of instructor results starting with overall summary

    # Sort instructors by A percentage descending
    sorted_insts = sorted(per_inst.items(), key=lambda x: x[1]["A"], reverse=True)

    # Add each instructor's data to output
    for name, counts in sorted_insts:
        instructors.append({"name": name, "grades": to_pct(counts)})

    return instructors


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@app.route("/")
@app.route("/index")
def home():
    """Homepage. Data is displayed on homepage whenever a new request is sent 
    with api_grades().
    """
    return render_template("index.html")


@app.route("/api/grades")
def api_grades():

    # Extract request parameters
    major_key = request.args.get("major", "")
    year_from = request.args.get("year_from", "2016")
    year_to   = request.args.get("year_to", "2023")

    major_name = MAJOR_MAP.get(major_key)  
    # Convert key to full major name

    # Validate major selection
    if not major_name or major_name not in DEGREES:
        return jsonify({"error": "Unknown major"}), 400

    valid_terms = ay_to_terms(year_from, year_to)  
    # Generate valid term list

    # Build course list with instructor data
    courses = [resolve_course(e, valid_terms) for e in DEGREES[major_name]]

    # Return structured JSON response
    return jsonify({
        "major": major_name,
        "years": f"AY{year_from}–AY{year_to}",
        "terms": [{
            "year": "Degree Sequence",
            "term": "Required Courses",
            "courses": courses,
        }],
    })


# ---------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)