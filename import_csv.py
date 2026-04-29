"""
File: import_csv.py
Description: Imports and cleans course grade data from CSV files into MongoDB.

Authors: 
- Renner, Caeleb

Group Name: group 8

Date last edited: 04/21/2026

Course: CIS 422 - Software Methodologies
Assignment: MaxGPA Project

---------------------------------------------------------------------

This script reads course grade data from one or more CSV files, cleans it,
and imports it into a MongoDB collection.

Key responsibilities:
- Load one or both CSV datasets (if available)
- Filter out rows that do not contain meaningful grade data
- Normalize missing or invalid values (NaN, "*") to 0
- Wait for MongoDB to be available before connecting (important for Docker environments)
- Replace existing collection data with cleaned data
"""

import os
import time
import pandas as pd
from pymongo import MongoClient

# File and database configuration
CSV_FILES = [
    "pub_rec_master_f2015-u2025.csv",
    "pub_rec_master_w2016-f2025.csv"
]

MONGO_URI = "mongodb://db:27017/"
DB_NAME = "maxgpa"
COLLECTION_NAME = "course_grades"

# All columns that represent grade counts in the dataset
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
    """
    while True:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            return client
        except Exception:
            print("Waiting for MongoDB...")
            time.sleep(2)


def clean_value(value):
    """
    Converts NaN and "*" values to 0.
    """
    if pd.isna(value) or value == "*":
        return 0
    return value


def has_real_grade_data(row):
    """
    Returns True if row contains at least one real grade value.
    """
    for col in GRADE_COLUMNS:
        value = row[col]
        if pd.notna(value) and value != "*" and str(value).strip() != "":
            return True
    return False

def load_available_csvs():
    """
    Loads all available CSV files.
    - If both exist → combine them
    - If one exists → use it
    - If none exist → error
    - Removes duplicate rows when both files contain overlapping data
    """
    dataframes = []

    for csv_file in CSV_FILES:
        if os.path.exists(csv_file):
            print(f"Loading CSV file: {csv_file}")
            df = pd.read_csv(csv_file, dtype={"NUMB": str})
            dataframes.append(df)
        else:
            print(f"CSV file not found, skipping: {csv_file}")

    if not dataframes:
        raise FileNotFoundError("No CSV files found.")

    combined_df = pd.concat(dataframes, ignore_index=True)

    before_count = len(combined_df)
    combined_df = combined_df.drop_duplicates()
    after_count = len(combined_df)

    print(f"Removed {before_count - after_count} duplicate rows.")

    return combined_df


def main():
    """
    Main data pipeline.
    """

    # Load one or both CSV files
    df = load_available_csvs()

    # Remove rows without meaningful grade data
    df = df[df.apply(has_real_grade_data, axis=1)]

    # Clean all values
    df = df.apply(lambda col: col.map(clean_value))

    # Convert to MongoDB documents
    documents = df.to_dict(orient="records")

    # Connect to MongoDB
    client = wait_for_mongo()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Replace existing data
    collection.delete_many({})
    collection.insert_many(documents)

    print("CSV data imported successfully.")


if __name__ == "__main__":
    main()