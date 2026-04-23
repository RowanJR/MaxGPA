"""
update_requirements.py
----------------------
Reads the degree requirements Excel sheet and updates degree_requirements.json.

All an admin needs to do:
  1. Update the Excel sheet with any course changes
  2. Run this script:  python update_requirements.py

Usage:
    python update_requirements.py --input Degree_Requirements.xlsx
    python update_requirements.py --input Degree_Requirements.xlsx --output degree_requirements.json
"""

import json
import argparse
import sys
import os

try:
    import openpyxl
except ImportError:
    print("[ERROR] openpyxl is required to read Excel files.")
    print("        Install it with: pip install openpyxl")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(value):
    """Strip whitespace from a cell value, return None if empty."""
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None


def is_degree_header(value):
    """
    Returns True if a row's first cell looks like a degree title
    (e.g. 'Bachelor of Science in ...') rather than a course code.
    """
    if not value:
        return False
    lower = value.lower()
    return (
        lower.startswith("bachelor") or
        lower.startswith("master") or
        lower.startswith("associate") or
        lower.startswith("doctor")
    )


def parse_or_slot(code_cell, title_cell, credits_cell, note_cell):
    """
    If the code cell contains ' or ' (e.g. 'MATH 251Z or MATH 246'),
    split it into an 'or' array. Otherwise return a plain course dict.
    """
    code_raw  = clean(code_cell)
    title_raw = clean(title_cell)
    credits   = None
    note      = clean(note_cell)

    # Parse credits as float if possible
    try:
        credits = float(credits_cell) if credits_cell is not None else None
    except (ValueError, TypeError):
        credits = None

    # Normalize newlines in cells to ' or ' so both formats are handled
    if code_raw:
        code_raw = code_raw.replace('\n', ' or ')
    if title_raw:
        title_raw = title_raw.replace('\n', ' or ')

    # Check for 'or' in code
    if code_raw and ' or ' in code_raw:
        codes  = [c.strip() for c in code_raw.split(' or ')]
        titles = [t.strip() for t in title_raw.split(' or ')] if title_raw and ' or ' in title_raw else []

        options = []
        for i, code in enumerate(codes):
            # Strip any leading 'or ' that Excel cells include literally
            clean_code = code.strip().removeprefix('or ').strip()
            opt = {"code": clean_code}
            if i < len(titles):
                clean_title = titles[i].strip().removeprefix('or ').strip()
                opt["title"] = clean_title
            options.append(opt)

        slot = {"or": options}
        if credits is not None:
            slot["credits"] = credits
        if note:
            slot["note"] = note
        return slot

    # Plain course
    slot = {}
    if code_raw:
        slot["code"] = code_raw
    if title_raw:
        slot["title"] = title_raw
    if credits is not None:
        slot["credits"] = credits
    if note:
        slot["note"] = note
    return slot if slot else None


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_excel(filepath: str) -> dict:
    """
    Reads the Excel sheet and returns a dict structured as:
    {
      "degrees": [
        {
          "name": "Bachelor of Science in ...",
          "courses": [ ... ]
        },
        ...
      ]
    }
    """
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active  # Read from the first/active sheet

    degrees = []
    current_degree = None

    for row in ws.iter_rows(values_only=True):
        # Grab the first four columns: code, title, note, credits
        # (matches the layout of Degree_Requirements.xlsx)
        col_a = clean(row[0]) if len(row) > 0 else None
        col_b = clean(row[1]) if len(row) > 1 else None
        col_c = clean(row[2]) if len(row) > 2 else None
        col_d = row[3]        if len(row) > 3 else None  # credits — keep raw for float conversion

        # Skip completely empty rows
        if not col_a and not col_b:
            continue

        # Degree header row (e.g. "Bachelor of Science in Computer Science")
        if is_degree_header(col_a):
            current_degree = {"name": col_a, "courses": []}
            degrees.append(current_degree)
            continue

        # Course row — only process if we're inside a degree
        if current_degree is None:
            continue

        slot = parse_or_slot(col_a, col_b, col_d, col_c)
        if slot:
            current_degree["courses"].append(slot)

    wb.close()

    if not degrees:
        print("[WARN] No degrees found in the Excel sheet. Check that degree headers start with 'Bachelor', 'Master', etc.")

    return {"degrees": degrees}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Update degree_requirements.json from the Excel sheet"
    )
    parser.add_argument("--input",  "-i", required=True,
                        help="Path to the Excel file (e.g. Degree_Requirements.xlsx)")
    parser.add_argument("--output", "-o", default="degree_requirements.json",
                        help="Path to write the updated JSON (default: degree_requirements.json)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] Excel file not found: {args.input}")
        sys.exit(1)

    print(f"[INFO] Reading '{args.input}'...")
    data = parse_excel(args.input)

    degree_names = [d["name"] for d in data["degrees"]]
    print(f"[INFO] Found {len(data['degrees'])} degree(s): {degree_names}")
    for d in data["degrees"]:
        print(f"       {d['name']}: {len(d['courses'])} course slots")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[DONE] '{args.output}' updated successfully.")


if __name__ == "__main__":
    main()
