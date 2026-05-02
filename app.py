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

app = Flask(__name__)
mongo_host = os.environ.get('DB_HOST', 'db')
client = MongoClient(mongo_host, 27017)
db = client.maxgpa


# ---------------------------------------------------------------------
# Static Configuration Data
# ---------------------------------------------------------------------

MAJOR_MAP = {
    "cs_bs":       "Bachelor of Science in Computer Science",
    "bs_business": "Bachelor of Science in Business Administration",
    "geog_bs":     "Bachelor of Science in Physics",
}

with open("degree_requirements.json") as f:
    _degree_data = json.load(f)

DEGREES = {d["name"]: d["courses"] for d in _degree_data["degrees"]}


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def ay_to_terms(year_from, year_to):
    terms = set()
    for ay in range(int(year_from), int(year_to) + 1):
        terms.add(f"Fall {ay}")
        terms.add(f"Winter {ay + 1}")
        terms.add(f"Spring {ay + 1}")
    return terms


def to_pct(counts):
    total = sum(counts.values())
    if total == 0:
        return {"A": 0, "B": 0, "C": 0, "DNF": 0}
    return {k: round(v / total * 100, 1) for k, v in counts.items()}


def get_class_info(subj, numb, valid_terms):
    numb = str(numb).strip()
    number_options = {numb}
    if numb.endswith("Z"):
        number_options.add(numb[:-1])
    else:
        number_options.add(numb + "Z")

    results = list(db.course_grades.find({
        "SUBJ": subj,
        "NUMB": {"$in": list(number_options)},
        "TERM_DESC": {"$in": list(valid_terms)}
    }))

    if not results:
        return []

    per_inst = {}
    all_totals = {"A": 0, "B": 0, "C": 0, "DNF": 0}

    for row in results:
        inst = str(row.get("INSTRUCTOR", "Unknown")).strip()
        if not inst:
            inst = "Unknown"
        if inst not in per_inst:
            per_inst[inst] = {"A": 0, "B": 0, "C": 0, "DNF": 0}

        a   = int(row.get("AP", 0)) + int(row.get("A", 0)) + int(row.get("AM", 0))
        b   = int(row.get("BP", 0)) + int(row.get("B", 0)) + int(row.get("BM", 0))
        c   = int(row.get("CP", 0)) + int(row.get("C", 0)) + int(row.get("CM", 0))
        dnf = int(row.get("DP", 0)) + int(row.get("D", 0)) + int(row.get("DM", 0)) + int(row.get("F", 0))

        per_inst[inst]["A"]   += a
        per_inst[inst]["B"]   += b
        per_inst[inst]["C"]   += c
        per_inst[inst]["DNF"] += dnf
        all_totals["A"]   += a
        all_totals["B"]   += b
        all_totals["C"]   += c
        all_totals["DNF"] += dnf

    instructors = [{"name": "All Instructors", "grades": to_pct(all_totals)}]
    for name, counts in sorted(per_inst.items(), key=lambda x: x[1]["A"], reverse=True):
        instructors.append({"name": name, "grades": to_pct(counts)})

    return instructors


def resolve_course(entry, valid_terms):
    if "or" in entry:
        for option in entry["or"]:
            subj, numb = option["code"].split()
            instructors = get_class_info(subj, numb, valid_terms)
            if instructors:
                return {
                    "code": option["code"],
                    "title": option["title"],
                    "credits": entry.get("credits", 4),
                    "instructors": instructors,
                }
        opt = entry["or"][0]
        return {
            "code": opt["code"],
            "title": opt["title"],
            "credits": entry.get("credits", 4),
            "instructors": [],
        }
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
    return render_template("index.html")


@app.route("/api/years")
def api_years():
    term_descs = db.course_grades.distinct("TERM_DESC")

    ay_set = set()

    for term in term_descs:
        parts = str(term).strip().split()
        if len(parts) != 2:
            continue

        season, year_str = parts[0], parts[1]

        try:
            cal_year = int(year_str)
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
    major_key = request.args.get("major", "")
    year_from = request.args.get("year_from", "2016")
    year_to   = request.args.get("year_to", "2023")

    major_name = MAJOR_MAP.get(major_key)
    if not major_name or major_name not in DEGREES:
        return jsonify({"error": "Unknown major"}), 400

    valid_terms = ay_to_terms(year_from, year_to)
    courses = [resolve_course(e, valid_terms) for e in DEGREES[major_name]]

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

    file = request.files["file"]

    if not file.filename or not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "File must be a .csv"}), 400

    try:
        content = file.read()
        df = pd.read_csv(io.BytesIO(content), dtype={"NUMB": str})
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {str(e)}"}), 422

    # Reuse import_csv.py cleaning logic
    df = df[df.apply(has_real_grade_data, axis=1)]
    df = df.apply(lambda col: col.map(clean_value))

    new_docs = df.to_dict(orient="records")

    if not new_docs:
        return jsonify({"error": "CSV contained no valid grade rows."}), 422

    collection = db.course_grades

    # Deduplicate against existing records
    def fingerprint(doc):
        return (
            str(doc.get("SUBJ", "")).strip(),
            str(doc.get("NUMB", "")).strip(),
            str(doc.get("TERM_DESC", "")).strip(),
            str(doc.get("INSTRUCTOR", "")).strip(),
        )

    existing_fps = set(
        fingerprint(doc)
        for doc in collection.find(
            {}, {"SUBJ": 1, "NUMB": 1, "TERM_DESC": 1, "INSTRUCTOR": 1, "_id": 0}
        )
    )

    to_insert = [d for d in new_docs if fingerprint(d) not in existing_fps]
    duplicates_removed = len(new_docs) - len(to_insert)

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