
import os
import json
from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient

app = Flask(__name__)

mongo_host = os.environ.get('DB_HOST', 'db')
client = MongoClient(mongo_host, 27017)
db = client.maxgpa

MAJOR_MAP = {
    "cs_bs":       "Bachelor of Science in Computer Science",
    "bs_business": "Bachelor of Science in Business Administration",
    "geog_bs":     "Bachelor of Science in Physics",
}

with open("degree_requirements.json") as f:
    _degree_data = json.load(f)

DEGREES = {d["name"]: d["courses"] for d in _degree_data["degrees"]}


def ay_to_terms(year_from, year_to):
    """Return the set of TERM_DESC strings covered by AY year_from through AY year_to.
    AY2016 = Fall 2016, Winter 2017, Spring 2017.
    """
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
    """Query MongoDB for a course and return per-instructor grade percentages
    with an 'All Instructors' aggregate as the first entry, sorted by % A desc."""
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

    sorted_insts = sorted(per_inst.items(), key=lambda x: x[1]["A"], reverse=True)
    for name, counts in sorted_insts:
        instructors.append({"name": name, "grades": to_pct(counts)})

    return instructors


def resolve_course(entry, valid_terms):
    """Handle both plain courses and 'or' alternatives. Returns a course dict."""
    if "or" in entry:
        for option in entry["or"]:
            parts = option["code"].split()
            subj, numb = parts[0], parts[1]
            instructors = get_class_info(subj, numb, valid_terms)
            if instructors:
                return {
                    "code": option["code"],
                    "title": option["title"],
                    "credits": entry.get("credits", 4),
                    "instructors": instructors,
                }
        # No data found for any option — show first alternative with empty data
        opt = entry["or"][0]
        return {
            "code": opt["code"],
            "title": opt["title"],
            "credits": entry.get("credits", 4),
            "instructors": [],
        }
    else:
        parts = entry["code"].split()
        subj, numb = parts[0], parts[1]
        return {
            "code": entry["code"],
            "title": entry["title"],
            "credits": entry.get("credits", 4),
            "instructors": get_class_info(subj, numb, valid_terms),
        }


@app.route("/")
@app.route("/index")
def home():
    return render_template("index.html")


@app.route("/api/grades")
def api_grades():
    major_key = request.args.get("major", "")
    year_from = request.args.get("year_from", "2016")
    year_to   = request.args.get("year_to",   "2023")

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
