"""
csv_to_json.py
--------------
Reads degree_requirements.json and outputs the required courses as JSON.
Student matching and grade lookup are handled separately.

Usage:
    python csv_to_json.py --requirements degree_requirements.json
    python csv_to_json.py --requirements degree_requirements.json --output out.json
    python csv_to_json.py --requirements degree_requirements.json --send
"""

import json
import argparse
import sys
import os


def load_requirements(filepath: str) -> dict:
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    print(f"[INFO] Loaded {len(data.get('degrees', []))} degree(s) from '{filepath}'")
    return data


def send_to_app(data: dict):
    try:
        import app
        if hasattr(app, "ingest_requirements"):
            app.ingest_requirements(data)
            print("[INFO] Sent to app.py via ingest_requirements()")
        elif hasattr(app, "load_data"):
            app.load_data(data)
            print("[INFO] Sent to app.py via load_data()")
        else:
            print("[WARN] app.py found but no known entry point (ingest_requirements / load_data).")
    except ImportError:
        print("[ERROR] Could not import app.py. Make sure it's in the same directory.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Read degree_requirements.json and output required courses as JSON"
    )
    parser.add_argument("--requirements", "-r", required=True, help="Path to degree_requirements.json")
    parser.add_argument("--output",       "-o", default=None,  help="Path to write output JSON (optional)")
    parser.add_argument("--send",         "-s", action="store_true", help="Send output directly to app.py")
    args = parser.parse_args()

    data = load_requirements(args.requirements)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] JSON written to '{args.output}'")
    elif not args.send:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    if args.send:
        send_to_app(data)

    print("[DONE]")


if __name__ == "__main__":
    main()
