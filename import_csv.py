import time
import pandas as pd
from pymongo import MongoClient

CSV_FILE = "pub_rec_master_f2015-u2025.csv"
MONGO_URI = "mongodb://db:27017/"
DB_NAME = "maxgpa"
COLLECTION_NAME = "course_grades"


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


def main():
    df = pd.read_csv(CSV_FILE, dtype={"NUMB": str})
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