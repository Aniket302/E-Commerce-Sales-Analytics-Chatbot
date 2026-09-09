import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "database" / "olist.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

FILES = {
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}


def create_database(connection):
    print("Creating database schema...")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema = file.read()

    connection.executescript(schema)
    connection.commit()

    print("Schema created successfully.\n")


def load_table(connection, table_name, filename):
    file_path = DATA_DIR / filename

    print(f"Loading {filename}...")

    df = pd.read_csv(file_path)

    # Insert into the existing table.
    df.to_sql(
        table_name,
        connection,
        if_exists="append",
        index=False
    )

    print(f"  -> {len(df):,} rows loaded into {table_name}")


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Start with a fresh database.
    if DB_PATH.exists():
        print("Removing existing database...")
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)

    try:
        create_database(connection)

        for table_name, filename in FILES.items():
            load_table(
                connection,
                table_name,
                filename
            )

        connection.commit()

        print("\nDatabase loaded successfully!")
        print(f"Database: {DB_PATH}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()