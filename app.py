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

Date Created:
04/16/2026

Modifications:
- 04/23/2026: Added course query and aggregation logic.
- 04/29/2026: Integrated API endpoint and improved data handling.
- 04/30/2026: Added support for course numbers with Z suffix and improved formatting.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os      # Used to read environment variables
import json    # Used to load degree requirements from JSON file
from flask import Flask, request, render_template, jsonify  # Web framework
from pymongo import MongoClient  # MongoDB connection


# ---------------------------------------------------------------------
# App and Database Setup
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
# Maps frontend major keys to full degree names


# Load degree requirement data from JSON file
with open("degree_requirements.json") as f:
    _degree_data = json.load(f)

# Convert JSON into dictionary mapping degree → courses
DEGREES = {d["name"]: d["courses"] for d in _degree_data["degrees"]}


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def ay_to_terms(year_from, year_to):
    """
    Convert academic year range into TERM_DESC values.
    """

    terms = set()  
    # Stores all valid term strings

    # Generate terms for each academic year
    for ay in range(int(year_from), int(year_to) + 1):
        terms.add(f"Fall {ay}")
        terms.add(f"Winter {ay + 1}")
        terms.add(f"Spring {ay + 1}")

    return terms


def to_pct(counts):
    """
    Convert raw grade counts into percentages.
    """

    total = sum(counts.values())  
    # Total number of grades

    # Prevent division by zero
    if total == 0:
        return {"A": 0, "B": 0, "C": 0, "DNF": 0}

    # Convert counts into percentage values
    return {k: round(v / total * 100, 1) for k, v in counts.items()}


def get_class_info(subj, numb, valid_terms):
    """
    Query MongoDB and return instructor grade distributions.
    """

    numb = str(numb).strip()  
    # Normalize course number

    number_options = {numb}  
    # Store possible course number variations

    # Support both "221" and "221Z"
    if numb.endswith("Z"):
        number_options.add(numb[:-1])
    else:
        number_options.add(numb + "Z")

    # Query database for matching courses
    results = list(db.course_grades.find({
        "SUBJ": subj,
        "NUMB": {"$in": list(number_options)},
        "TERM_DESC": {"$in": list(valid_terms)}
    }))

    # Return empty list if no results found
    if not results:
        return []

    per_inst = {}  
    # Stores grade totals per instructor

    all_totals = {"A": 0, "B": 0, "C": 0, "DNF": 0}  
    # Stores overall totals across all instructors

    # Process each database row
    for row in results:

        inst = str(row.get("INSTRUCTOR", "Unknown")).strip()
        if not inst:
            inst = "Unknown"

        # Initialize instructor entry if not already present
        if inst not in per_inst:
            per_inst[inst] = {"A": 0, "B": 0, "C": 0, "DNF": 0}

        # Combine grade categories
        a   = int(row.get("AP", 0)) + int(row.get("A", 0)) + int(row.get("AM", 0))
        b   = int(row.get("BP", 0)) + int(row.get("B", 0)) + int(row.get("BM", 0))
        c   = int(row.get("CP", 0)) + int(row.get("C", 0)) + int(row.get("CM", 0))
        dnf = int(row.get("DP", 0)) + int(row.get("D", 0)) + int(row.get("DM", 0)) + int(row.get("F", 0))

        # Update instructor totals
        per_inst[inst]["A"]   += a
        per_inst[inst]["B"]   += b
        per_inst[inst]["C"]   += c
        per_inst[inst]["DNF"] += dnf

        # Update overall totals
        all_totals["A"]   += a
        all_totals["B"]   += b
        all_totals["C"]   += c
        all_totals["DNF"] += dnf

    # Add aggregate "All Instructors" entry first
    instructors = [{"name": "All Instructors", "grades": to_pct(all_totals)}]

    # Sort instructors by highest A percentage
    sorted_insts = sorted(per_inst.items(), key=lambda x: x[1]["A"], reverse=True)

    # Add each instructor to output
    for name, counts in sorted_insts:
        instructors.append({"name": name, "grades": to_pct(counts)})

    return instructors


def resolve_course(entry, valid_terms):
    """
    Resolve a course entry, including handling "or" alternatives.
    """

    # Handle alternative course options
    if "or" in entry:
        for option in entry["or"]:
            subj, numb = option["code"].split()

            instructors = get_class_info(subj, numb, valid_terms)

            # Return first option with available data
            if instructors:
                return {
                    "code": option["code"],
                    "title": option["title"],
                    "credits": entry.get("credits", 4),
                    "instructors": instructors,
                }

        # If no options have data, return first option with empty list
        opt = entry["or"][0]
        return {
            "code": opt["code"],
            "title": opt["title"],
            "credits": entry.get("credits", 4),
            "instructors": [],
        }

    # Handle normal course
    else:
        subj, numb = entry["code"].split()
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
    Render homepage.
    """
    return render_template("index.html")


@app.route("/api/grades")
def api_grades():
    """
    Return grade data for selected major and year range.
    """

    # Get query parameters from request
    major_key = request.args.get("major", "")
    year_from = request.args.get("year_from", "2016")
    year_to   = request.args.get("year_to", "2023")

    # Map key to full major name
    major_name = MAJOR_MAP.get(major_key)

    # Validate major selection
    if not major_name or major_name not in DEGREES:
        return jsonify({"error": "Unknown major"}), 400

    # Generate valid term list
    valid_terms = ay_to_terms(year_from, year_to)

    # Build course list
    courses = [resolve_course(e, valid_terms) for e in DEGREES[major_name]]

    # Return structured JSON response
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


# ---------------------------------------------------------------------
# Program Entry Point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)