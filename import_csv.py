"""
File: import_csv.py

Purpose:
Loads course grade CSV files, cleans the data, removes duplicate records, and
imports the cleaned records into MongoDB.

System Context:
This file is part of the MaxGPA system. MaxGPA is a Flask and MongoDB web
application that helps users view grade distribution data for courses in
selected degree programs. This file acts as the data import pipeline that
prepares raw CSV grade data for use by the Flask backend in app.py.

Authors:
- Rowan Moore
- Caeleb Renner

Date Created:
04/16/2026

Modifications:
- 04/21/2026: Improved filtering of invalid grade data.
- 04/23/2026: Expanded dataset handling.
- 04/29/2026: Added support for multiple CSV files and Z-suffix course numbers.
- 04/30/2026: Refactored to load CSV files from Course_Grades directory.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os              # Used for file system operations (folder checking, file listing)
import time            # Used to delay retries when waiting for MongoDB
import pandas as pd    # Used for reading and cleaning CSV data
from pymongo import MongoClient  # Used to connect to MongoDB database


# ---------------------------------------------------------------------
# Configuration Variables
# ---------------------------------------------------------------------

COURSE_GRADES_FOLDER = "Course_Grades"  
# Folder containing all CSV files to be imported

MONGO_URI = "mongodb://db:27017/"  
# Connection string for MongoDB (default assumes Docker container named "db")

DB_NAME = "maxgpa"  
# Name of the MongoDB database

COLLECTION_NAME = "course_grades"  
# Name of the collection where course data is stored


# ---------------------------------------------------------------------
# Grade Columns Definition
# ---------------------------------------------------------------------

GRADE_COLUMNS = {
    "AP","A","AM","BP","B","BM",
    "CP","C","CM","DP","D","DM",
    "F","P","N","OTHER","W"
}
# Set of all grade-related columns used to determine if a row has real data


# ---------------------------------------------------------------------
# MongoDB Connection Handling
# ---------------------------------------------------------------------

def wait_for_mongo():
    """
    Continuously attempts to connect to MongoDB until successful.
    This prevents the script from failing if MongoDB is not ready yet.
    """

    # Keep trying to connect until successful
    while True:
        try:
            # Attempt to connect to MongoDB with short timeout
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)

            # Verify connection by sending a ping command
            client.admin.command("ping")

            # If successful, return the connected client
            return client

        except Exception:
            # If connection fails, wait and retry
            print("Waiting for MongoDB...")
            time.sleep(2)


# ---------------------------------------------------------------------
# Data Cleaning Functions
# ---------------------------------------------------------------------

def clean_value(value):
    """
    Replace missing or hidden values with 0.
    """

    # If value is NaN or "*" (hidden), replace with 0
    if pd.isna(value) or value == "*":
        return 0

    # Otherwise return original value
    return value


def has_real_grade_data(row):
    """
    Determine if a row contains at least one valid grade value.
    """

    # Check each grade column in the row
    for col in GRADE_COLUMNS:
        value = row[col]

        # If any valid value exists, return True
        if pd.notna(value) and value != "*" and str(value).strip() != "":
            return True

    # If no valid values found, return False
    return False


# ---------------------------------------------------------------------
# CSV Loading and Processing
# ---------------------------------------------------------------------

def load_available_csvs():
    """
    Load all CSV files from the Course_Grades folder and combine them.
    """

    dataframes = []  
    # List to store each CSV file's DataFrame

    # Check if folder exists
    if not os.path.isdir(COURSE_GRADES_FOLDER):
        raise FileNotFoundError(f"Folder not found: {COURSE_GRADES_FOLDER}")

    # Get all CSV files in the folder
    csv_files = [
        file for file in os.listdir(COURSE_GRADES_FOLDER)
        if file.lower().endswith(".csv")
    ]

    # If no CSV files found, raise error
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {COURSE_GRADES_FOLDER}")

    # Loop through each CSV file and load it
    for csv_file in csv_files:
        path = os.path.join(COURSE_GRADES_FOLDER, csv_file)  
        # Full path to the CSV file

        print(f"Loading CSV file: {path}")

        # Read CSV into DataFrame (NUMB as string preserves values like "221Z")
        df = pd.read_csv(path, dtype={"NUMB": str})

        # Add DataFrame to list
        dataframes.append(df)

    # Combine all DataFrames into one
    combined_df = pd.concat(dataframes, ignore_index=True)

    before_count = len(combined_df)  
    # Number of rows before removing duplicates

    # Remove duplicate rows
    combined_df = combined_df.drop_duplicates()

    after_count = len(combined_df)  
    # Number of rows after removing duplicates

    print(f"Removed {before_count - after_count} duplicate rows.")

    return combined_df


# ---------------------------------------------------------------------
# Main Execution Pipeline
# ---------------------------------------------------------------------

def main():
    """
    Main execution function that runs the full data import process.
    """

    # Step 1: Load all CSV data
    df = load_available_csvs()

    # Step 2: Remove rows with no valid grade data
    df = df[df.apply(has_real_grade_data, axis=1)]

    # Step 3: Clean all values in DataFrame
    df = df.apply(lambda col: col.map(clean_value))

    # Step 4: Convert DataFrame into MongoDB document format
    documents = df.to_dict(orient="records")

    # Step 5: Connect to MongoDB
    client = wait_for_mongo()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Step 6: Clear existing data in collection
    collection.delete_many({})

    # Step 7: Insert new cleaned data
    collection.insert_many(documents)

    print("CSV data imported successfully.")


# ---------------------------------------------------------------------
# Program Entry Point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # Run main function when script is executed directly
    main()