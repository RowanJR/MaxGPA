"""
File: update_requirements.py

Purpose:
Reads an Excel file containing degree requirements and updates the
degree_requirements.json file used by the MaxGPA application.

System Context:
This file is part of the MaxGPA system. MaxGPA uses degree_requirements.json
to determine which courses belong to each degree program. This script lets an
admin update the Excel spreadsheet and regenerate the JSON file without editing
the JSON manually.

Authors:
- Hayden Oelke

Date Created:
04/23/2026

Modifications:
- 04/23/2026: Added Excel-to-JSON degree requirement update script.
- 04/30/2026: Added detailed comments to match project documentation requirements.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import json      # Used to write parsed degree requirement data to a JSON file.
import argparse  # Used to read command-line input and output file arguments.
import sys       # Used to exit the program when required dependencies are missing.
import os        # Used to check whether the input Excel file exists.


# ---------------------------------------------------------------------------
# Optional package import
# ---------------------------------------------------------------------------

# Try to import openpyxl, which is required for reading Excel files.
try:
    import openpyxl  # Used to load and read .xlsx spreadsheet files.

# If openpyxl is missing, show install instructions and stop the script.
except ImportError:
    print("[ERROR] openpyxl is required to read Excel files.")
    print("        Install it with: pip install openpyxl")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def clean(value):
    """
    Strip whitespace from a spreadsheet cell value.

    Returns:
        None if the value is empty, otherwise the cleaned string value.
    """

    # Empty Excel cells should be treated as missing values.
    if value is None:
        return None

    # Convert the value to a string and remove extra whitespace.
    v = str(value).strip()

    # Return the cleaned value only if it still contains text.
    return v if v else None


def is_degree_header(value):
    """
    Check whether a row appears to contain a degree title.

    Degree rows are identified by common degree-starting words such as
    Bachelor, Master, Associate, or Doctor.
    """

    # Missing values cannot be degree headers.
    if not value:
        return False

    # Convert to lowercase so matching works regardless of capitalization.
    lower = value.lower()

    # Return True if the cell starts with a known degree type.
    return (
        lower.startswith("bachelor") or
        lower.startswith("master") or
        lower.startswith("associate") or
        lower.startswith("doctor")
    )


def parse_or_slot(code_cell, title_cell, credits_cell, note_cell):
    """
    Convert one spreadsheet course row into a JSON-ready course slot.

    This function supports both:
    - normal course rows
    - rows with alternatives, such as "MATH 251Z or MATH 246"
    """

    # Clean the course code cell.
    code_raw = clean(code_cell)

    # Clean the course title cell.
    title_raw = clean(title_cell)

    # Store parsed credits; starts as None in case the cell is empty or invalid.
    credits = None

    # Clean the note cell.
    note = clean(note_cell)

    # Try to convert the credits cell into a floating-point number.
    try:
        credits = float(credits_cell) if credits_cell is not None else None

    # If credits are not numeric, ignore them instead of crashing.
    except (ValueError, TypeError):
        credits = None

    # Treat newline-separated alternatives like "or" alternatives.
    if code_raw:
        code_raw = code_raw.replace('\n', ' or ')

    # Treat newline-separated titles like "or" alternatives.
    if title_raw:
        title_raw = title_raw.replace('\n', ' or ')

    # If the course code contains alternatives, build an "or" course slot.
    if code_raw and ' or ' in code_raw:
        codes = [c.strip() for c in code_raw.split(' or ')]

        # Split titles only if the title cell also contains alternatives.
        titles = [t.strip() for t in title_raw.split(' or ')] if title_raw and ' or ' in title_raw else []

        # Store each alternative course option.
        options = []

        # Build a JSON object for each course alternative.
        for i, code in enumerate(codes):

            # Remove extra literal "or" text that may come from the spreadsheet.
            clean_code = code.strip().removeprefix('or ').strip()

            # Create the option dictionary with the required course code.
            opt = {"code": clean_code}

            # Add the matching title if one exists.
            if i < len(titles):
                clean_title = titles[i].strip().removeprefix('or ').strip()
                opt["title"] = clean_title

            # Add this alternative option to the list.
            options.append(opt)

        # Store alternatives under the "or" key.
        slot = {"or": options}

        # Include credits if the spreadsheet provided a valid number.
        if credits is not None:
            slot["credits"] = credits

        # Include notes if the spreadsheet provided one.
        if note:
            slot["note"] = note

        # Return the completed alternative course slot.
        return slot

    # Start building a normal course slot for rows without alternatives.
    slot = {}

    # Add the course code if present.
    if code_raw:
        slot["code"] = code_raw

    # Add the course title if present.
    if title_raw:
        slot["title"] = title_raw

    # Add credits if valid.
    if credits is not None:
        slot["credits"] = credits

    # Add note if present.
    if note:
        slot["note"] = note

    # Return the course slot only if it contains data.
    return slot if slot else None


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_excel(filepath: str) -> dict:
    """
    Read the Excel sheet and convert it into the degree_requirements.json format.

    Expected output format:
    {
      "degrees": [
        {
          "name": "Bachelor of Science in ...",
          "courses": [...]
        }
      ]
    }
    """

    # Load the Excel workbook in read-only mode for safety and efficiency.
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)

    # Use the active sheet as the source of degree requirement data.
    ws = wb.active

    # Store all parsed degree objects.
    degrees = []

    # Track the degree currently being read.
    current_degree = None

    # Process each row in the worksheet.
    for row in ws.iter_rows(values_only=True):

        # Read the first column as the course code or degree header.
        col_a = clean(row[0]) if len(row) > 0 else None

        # Read the second column as the course title.
        col_b = clean(row[1]) if len(row) > 1 else None

        # Read the third column as an optional note.
        col_c = clean(row[2]) if len(row) > 2 else None

        # Read the fourth column as credits, keeping the raw value for conversion.
        col_d = row[3] if len(row) > 3 else None

        # Skip rows that do not contain a degree title or course data.
        if not col_a and not col_b:
            continue

        # Start a new degree section when a degree header row is found.
        if is_degree_header(col_a):
            current_degree = {"name": col_a, "courses": []}
            degrees.append(current_degree)
            continue

        # Ignore course rows before any degree header has been found.
        if current_degree is None:
            continue

        # Convert this spreadsheet row into a course slot dictionary.
        slot = parse_or_slot(col_a, col_b, col_d, col_c)

        # Add valid course slots to the current degree.
        if slot:
            current_degree["courses"].append(slot)

    # Close the workbook after all rows are processed.
    wb.close()

    # Warn the user if no degree headers were found.
    if not degrees:
        print("[WARN] No degrees found in the Excel sheet. Check that degree headers start with 'Bachelor', 'Master', etc.")

    # Return the final JSON-ready degree data.
    return {"degrees": degrees}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """
    Read command-line arguments, parse the Excel file, and write the JSON output.
    """

    # Create the command-line argument parser.
    parser = argparse.ArgumentParser(
        description="Update degree_requirements.json from the Excel sheet"
    )

    # Required input argument for the Excel file path.
    parser.add_argument("--input", "-i", required=True,
                        help="Path to the Excel file (e.g. Degree_Requirements.xlsx)")

    # Optional output argument for the JSON file path.
    parser.add_argument("--output", "-o", default="degree_requirements.json",
                        help="Path to write the updated JSON (default: degree_requirements.json)")

    # Parse command-line arguments into an args object.
    args = parser.parse_args()

    # Stop early if the requested Excel input file does not exist.
    if not os.path.exists(args.input):
        print(f"[ERROR] Excel file not found: {args.input}")
        sys.exit(1)

    # Show which file is being read.
    print(f"[INFO] Reading '{args.input}'...")

    # Parse the Excel file into JSON-ready data.
    data = parse_excel(args.input)

    # Build a list of degree names for the status message.
    degree_names = [d["name"] for d in data["degrees"]]

    # Print how many degrees were found.
    print(f"[INFO] Found {len(data['degrees'])} degree(s): {degree_names}")

    # Print how many course slots each degree contains.
    for d in data["degrees"]:
        print(f"       {d['name']}: {len(d['courses'])} course slots")

    # Open the output JSON file for writing.
    with open(args.output, "w", encoding="utf-8") as f:

        # Write the parsed data to the JSON file in readable format.
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Confirm successful completion.
    print(f"[DONE] '{args.output}' updated successfully.")


# ---------------------------------------------------------------------------
# Program entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # Only run main when this script is executed directly.
    main()