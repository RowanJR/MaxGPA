"""
File: CSV_to_JSON_requirements.py

Purpose:
Reads degree_requirements.json and outputs the required course data as JSON.
This script can print the data, write it to a file, or send it directly to app.py.

System Context:
This file is part of the MaxGPA system. It provides a utility for exporting or
transferring degree requirement data used by the backend (app.py). It does not
perform grade lookup or database queries.

Authors:
- Hayden Oelke

Date Created:
04/23/2026

Modifications:
- 04/23/2026: Initial implementation for loading and exporting degree requirement data.
- 04/30/2026: Added detailed comments to meet documentation requirements.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import json      # Used to read and write JSON data
import argparse  # Used to parse command-line arguments
import sys       # Used to exit the program on errors
import os        # Used to check file existence


# ---------------------------------------------------------------------
# Load Degree Requirements
# ---------------------------------------------------------------------

def load_requirements(filepath: str) -> dict:
    """
    Load degree requirement data from a JSON file.
    """

    # Check if file exists before attempting to open it
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    # Open and read JSON file
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    # Print confirmation message with number of degrees loaded
    print(f"[INFO] Loaded {len(data.get('degrees', []))} degree(s) from '{filepath}'")

    return data


# ---------------------------------------------------------------------
# Optional App Integration
# ---------------------------------------------------------------------

def send_to_app(data: dict):
    """
    Send degree requirement data directly to app.py if supported.
    """

    try:
        # Attempt to import backend application
        import app

        # Check for supported data ingestion functions
        if hasattr(app, "ingest_requirements"):
            app.ingest_requirements(data)
            print("[INFO] Sent to app.py via ingest_requirements()")

        elif hasattr(app, "load_data"):
            app.load_data(data)
            print("[INFO] Sent to app.py via load_data()")

        else:
            print("[WARN] app.py found but no known entry point (ingest_requirements / load_data).")

    # Handle missing app.py
    except ImportError:
        print("[ERROR] Could not import app.py. Make sure it's in the same directory.")
        sys.exit(1)


# ---------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------

def main():
    """
    Parse command-line arguments and determine how to output JSON data.
    """

    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Read degree_requirements.json and output required courses as JSON"
    )

    # Required argument: input JSON file
    parser.add_argument(
        "--requirements", "-r",
        required=True,
        help="Path to degree_requirements.json"
    )

    # Optional argument: output file path
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path to write output JSON (optional)"
    )

    # Optional flag: send data to app.py
    parser.add_argument(
        "--send", "-s",
        action="store_true",
        help="Send output directly to app.py"
    )

    # Parse arguments
    args = parser.parse_args()

    # Load degree requirement data
    data = load_requirements(args.requirements)

    # If output file is specified, write JSON to file
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[INFO] JSON written to '{args.output}'")

    # If no output file and no send flag, print JSON to console
    elif not args.send:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    # If send flag is set, send data to app.py
    if args.send:
        send_to_app(data)

    # Final confirmation message
    print("[DONE]")


# ---------------------------------------------------------------------
# Program Entry Point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()