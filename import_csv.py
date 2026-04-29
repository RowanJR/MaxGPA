"""
File: import_csv.py
Description: Imports and cleans course grade data from a CSV file into MongoDB.

Authors: 
- Renner, Caeleb


Group Name: group 8

Date last edited: 04/21/2026

Course: CIS 422 - Software Methodologies
Assignment: MaxGPA Project

---------------------------------------------------------------------

This script reads course grade data from a CSV file, cleans it, and imports it into a MongoDB collection.

Key responsibilities:
- Filter out rows that do not contain meaningful grade data
- Normalize missing or invalid values (NaN, "*") to 0
- Wait for MongoDB to be available before connecting (important for Docker environments)
- Replace existing collection data with cleaned data
"""

import time
import pandas as pd
from pymongo import MongoClient

# File and database configuration
CSV_FILE = "pub_rec_master_w2016-f2025.csv"
MONGO_URI = "mongodb://db:27017/"
DB_NAME = "maxgpa"
COLLECTION_NAME = "course_grades"

# All columns that represent grade counts in the dataset
# Used to check whether a row contains meaningful grade data
GRADE_COLUMNS = {
    "AP", 
    "A",
    "AM",
    "BP",
    "B",
    "BM",
    "CP",
    "C",
    "CM",
    "DP",
    "D",
    "DM",
    "F",
    "P",
    "N",
    "OTHER",
    "W"
}

def wait_for_mongo():
    """
    Continuously attempts to connect to MongoDB until successful.
    This is especially important in containerized environments where
    the database may not be ready when the script starts.
    """
    while True:
        try:
            # Short timeout prevents long blocking if DB is not ready
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")  # Simple check to confirm connection
            return client
        except Exception:
            print("Waiting for MongoDB...")
            time.sleep(2)


def clean_value(value):
    """
    Normalizes grade count values:
    - Converts NaN (missing values) and "*" (special marker in dataset) to 0
    - Leaves valid numeric values unchanged

    This ensures all grade columns can be safely used in calculations later.
    """
    if pd.isna(value) or value == "*":
        return 0
    return value


def has_real_grade_data(row):
    """
    Determines whether a row contains any meaningful grade data.

    A row is considered valid if at least one grade column:
    - Is not NaN
    - Is not "*"
    - Is not an empty string

    Rows without real data are filtered out to avoid storing useless records.
    """
    for col in GRADE_COLUMNS:
        value = row[col]
        if pd.notna(value) and value != "*" and str(value).strip() != "":
            return True
    return False


def main():
    """
    Main data pipeline:
    1. Load CSV into a DataFrame
    2. Filter out rows with no valid grade data
    3. Clean/normalize all values
    4. Convert to JSON-like documents
    5. Replace MongoDB collection contents with cleaned data
    """

    # Load CSV; ensure course number is treated as a string (prevents formatting issues)
    df = pd.read_csv(CSV_FILE, dtype={"NUMB": str})

    # Remove rows that don't contain any meaningful grade data
    df = df[df.apply(has_real_grade_data, axis=1)]

    # Apply cleaning function to every value in the DataFrame
    # (column-wise mapping for efficiency)
    df = df.apply(lambda col: col.map(clean_value))

    # Convert DataFrame into a list of dictionaries for MongoDB insertion
    documents = df.to_dict(orient="records")

    # Connect to MongoDB (waits until available)
    client = wait_for_mongo()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Clear existing data to avoid duplicates or stale records
    collection.delete_many({})

    # Insert cleaned dataset into MongoDB
    collection.insert_many(documents)

    print("CSV data imported successfully.")


if __name__ == "__main__":
    main()