"""
File: CSV_to_JSON_requirements.py

Purpose:
Reads degree_requirements.json and outputs the required course data as JSON.

System Context:
This file is part of the MaxGPA system. MaxGPA uses degree_requirements.json
to store the required courses for each supported degree program. This script
loads that JSON file and either prints it, writes it to another JSON file, or
sends it to app.py if a supported app entry point exists.

Authors:
- Hayden Oelke

Date Created:
04/23/2026

Modifications:
- 04/23/2026: Added script for reading and exporting degree requirement JSON data.
- 04/30/2026: Added detailed comments to match project documentation requirements.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import json      # Used to read and write JSON data.
import argparse  # Used to handle command-line arguments.
import sys       # Used to exit the program after unrecoverable errors.
import os        # Used to check whether input files exist.


# ---------------------------------------------------------------------------
# Load degree requirements
# ---------------------------------------------------------------------------

def load_requirements(filepath: str) -> dict:
    """
    Load degree requirement data from a JSON file.
    """

    # Stop the script if the provided requirements file does not exist.
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    # Open the JSON file using UTF-8 encoding.
    with open(filepath, encoding="utf-8") as f:

        # Read the JSON file into a Python dictionary.
        data = json.load(f)

    # Print how many degree entries were loaded for user confirmation.
    print(f"[INFO] Loaded {len(data.get('degrees', []))} degree(s) from '{filepath}'")

    # Return the loaded degree requirement data.
    return data


# ---------------------------------------------------------------------------
# Optional app.py transfer
# ---------------------------------------------------------------------------

def send_to_app(data: dict):
    """
    Send loaded degree requirement data directly to app.py if possible.
    """

    # Try to import app.py from the same directory.
    try:
        import app

        # Use ingest_requirements() if app.py provides that function.
        if hasattr(app, "ingest_requirements"):
            app.ingest_requirements(data)
            print("[INFO] Sent to app.py via ingest_requirements()")

        # Otherwise use load_data() if app.py provides that function.
        elif hasattr(app, "load_data"):
            app.load_data(data)
            print("[INFO] Sent to app.py via load_data()")

        # If neither entry point exists, warn the user.
        else:
            print("[WARN] app.py found but no known entry point (ingest_requirements / load_data).")

    # If app.py cannot be imported, print an error and stop.
    except ImportError:
        print("[ERROR] Could not import app.py. Make sure it's in the same directory.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """
    Read command-line arguments and decide how to output the JSON data.
    """

    # Create the command-line argument parser.
    parser = argparse.ArgumentParser(
        description="Read degree_requirements.json and output required courses as JSON"
    )

    # Required argument for the input requirements JSON file.
    parser.add_argument("--requirements", "-r", required=True,
                        help="Path to degree_requirements.json")

    # Optional argument for writing the output to a different JSON file.
    parser.add_argument("--output", "-o", default=None,
                        help="Path to write output JSON (optional)")

    # Optional flag for sending the data directly to app.py.
    parser.add_argument("--send", "-s", action="store_true",
                        help="Send output directly to app.py")

    # Parse command-line arguments into an args object.
    args = parser.parse_args()

    # Load the degree requirement data from the input file.
    data = load_requirements(args.requirements)

    # If an output file was provided, write the JSON data to that file.
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:

            # Write JSON in a readable format while preserving special characters.
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Confirm that the output file was written.
        print(f"[INFO] JSON written to '{args.output}'")

    # If no output file and no send flag are provided, print the JSON to console.
    elif not args.send:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    # If requested, send the loaded data directly to app.py.
    if args.send:
        send_to_app(data)

    # Print final completion message.
    print("[DONE]")


# ---------------------------------------------------------------------------
# Program entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # Run main only when this script is executed directly.
    main()