import time
import pandas as pd
from pymongo import MongoClient

CSV_FILE = "pub_rec_master_f2015-u2025.csv"
MONGO_URI = "mongodb://db:27017/"
DB_NAME = "maxgpa"
COLLECTION_NAME = "course_grades"

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
    while True:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            return client
        except Exception:
            print("Waiting for MongoDB...")
            time.sleep(2)


def clean_value(value):
    if pd.isna(value) or value == "*":
        return 0
    return value

def has_real_grade_data(row):
    for col in GRADE_COLUMNS:
        value = row[col]
        if pd.notna(value) and value != "*" and str(value).strip() != "":
            return True
    return False


def main():
    df = pd.read_csv(CSV_FILE, dtype={"NUMB": str})

    df = df[df.apply(has_real_grade_data, axis=1)]

    df = df.apply(lambda col: col.map(clean_value))

    documents = df.to_dict(orient="records")

    client = wait_for_mongo()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    collection.delete_many({})
    collection.insert_many(documents)

    print("CSV data imported successfully.")


if __name__ == "__main__":
    main()