"""
File: update_requirements.py

Purpose:
Reads an Excel file containing degree requirements and updates the
degree_requirements.json file used by the MaxGPA system.

System Context:
This file is part of the MaxGPA system. It allows administrators to update
degree requirement data by modifying an Excel spreadsheet and regenerating
the JSON file used by the backend (app.py). This removes the need to manually
edit JSON files.

Authors:
- Hayden Oelke

Date Created:
04/23/2026

Modifications:
- 04/23/2026: Initial implementation for Excel-to-JSON conversion.
- 04/30/2026: Added detailed comments to meet documentation requirements.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import json      # Used to write parsed data to JSON file
import argparse  # Used to parse command-line arguments
import sys       # Used to exit program on error
import os        # Used to check file existence


# ---------------------------------------------------------------------------
# External Dependency (Excel Reader)
# ---------------------------------------------------------------------------

# Attempt to import openpyxl for reading Excel files
try:
    import openpyxl  # Library for working with Excel (.xlsx) files

# If openpyxl is missing, display error and exit
except ImportError:
    print("[ERROR] openpyxl is required to read Excel files.")
    print("        Install it with: pip install openpyxl")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def clean(value):
    """
    Clean a spreadsheet cell value by stripping whitespace.
    """

    # Return None for empty cells
    if value is None:
        return None

    # Convert value to string and strip whitespace
    v = str(value).strip()

    # Return cleaned value or None if empty
    return v if v else None


def is_degree_header(value):
    """
    Determine whether a row represents a degree header.
    """

    # Missing values cannot be headers
    if not value:
        return False

    # Normalize value to lowercase
    lower = value.lower()

    # Check for common degree prefixes
    return (
        lower.startswith("bachelor") or
        lower.startswith("master") or
        lower.startswith("associate") or
        lower.startswith("doctor")
    )


def parse_or_slot(code_cell, title_cell, credits_cell, note_cell):
    """
    Convert a row into a course slot dictionary.
    Supports both single courses and "or" alternatives.
    """

    code_raw  = clean(code_cell)   # Clean course code
    title_raw = clean(title_cell)  # Clean course title
    credits   = None               # Store numeric credit value
    note      = clean(note_cell)   # Clean optional note

    # Attempt to convert credits to float
    try:
        credits = float(credits_cell) if credits_cell is not None else None
    except (ValueError, TypeError):
        credits = None

    # Normalize newline-separated alternatives into "or"
    if code_raw:
        code_raw = code_raw.replace('\n', ' or ')
    if title_raw:
        title_raw = title_raw.replace('\n', ' or ')

    # Handle "or" course options
    if code_raw and ' or ' in code_raw:
        codes  = [c.strip() for c in code_raw.split(' or ')]
        titles = [t.strip() for t in title_raw.split(' or ')] if title_raw and ' or ' in title_raw else []

        options = []

        # Build each alternative course option
        for i, code in enumerate(codes):
            clean_code = code.strip().removeprefix('or ').strip()
            opt = {"code": clean_code}

            # Add matching title if available
            if i < len(titles):
                clean_title = titles[i].strip().removeprefix('or ').strip()
                opt["title"] = clean_title

            options.append(opt)

        slot = {"or": options}

        # Add optional fields if available
        if credits is not None:
            slot["credits"] = credits
        if note:
            slot["note"] = note

        return slot

    # Handle standard single course row
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
# Core Parser
# ---------------------------------------------------------------------------

def parse_excel(filepath: str) -> dict:
    """
    Read Excel file and convert it into degree_requirements.json format.
    """

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    # Load workbook in read-only mode

    ws = wb.active
    # Use first sheet as data source

    degrees = []
    # Store all parsed degree objects

    current_degree = None
    # Track current degree being processed

    # Process each row in the sheet
    for row in ws.iter_rows(values_only=True):

        # Extract columns from row
        col_a = clean(row[0]) if len(row) > 0 else None
        col_b = clean(row[1]) if len(row) > 1 else None
        col_c = clean(row[2]) if len(row) > 2 else None
        col_d = row[3] if len(row) > 3 else None

        # Skip empty rows
        if not col_a and not col_b:
            continue

        # Start a new degree when header is found
        if is_degree_header(col_a):
            current_degree = {"name": col_a, "courses": []}
            degrees.append(current_degree)
            continue

        # Skip rows before any degree is defined
        if current_degree is None:
            continue

        # Convert row into course slot
        slot = parse_or_slot(col_a, col_b, col_d, col_c)

        # Add valid course slot
        if slot:
            current_degree["courses"].append(slot)

    wb.close()

    # Warn if no degrees found
    if not degrees:
        print("[WARN] No degrees found in the Excel sheet.")

    return {"degrees": degrees}


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

def main():
    """
    Parse arguments, read Excel file, and write updated JSON file.
    """

    parser = argparse.ArgumentParser(
        description="Update degree_requirements.json from the Excel sheet"
    )

    parser.add_argument("--input", "-i", required=True,
                        help="Path to Excel file")

    parser.add_argument("--output", "-o", default="degree_requirements.json",
                        help="Output JSON file path")

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.input):
        print(f"[ERROR] Excel file not found: {args.input}")
        sys.exit(1)

    print(f"[INFO] Reading '{args.input}'...")

    # Parse Excel file
    data = parse_excel(args.input)

    # Print summary of parsed data
    for d in data["degrees"]:
        print(f"{d['name']}: {len(d['courses'])} course slots")

    # Write JSON output file
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[DONE] '{args.output}' updated successfully.")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()