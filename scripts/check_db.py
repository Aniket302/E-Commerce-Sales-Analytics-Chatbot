import sqlite3


DB_PATH = "database/olist.db"


def main():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    print("\nTABLES")
    print("=" * 40)

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name;
    """)

    for (table_name,) in cursor.fetchall():
        print(table_name)

    print("\nROW COUNTS")
    print("=" * 40)

    tables = [
        "customers",
        "sellers",
        "products",
        "category_translation",
        "orders",
        "order_items",
        "order_payments",
        "order_reviews",
        "geolocation",
    ]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        print(f"{table:25} {count:,}")

    connection.close()


if __name__ == "__main__":
    main()

## OUTPUT

# TABLES
# ========================================
# category_translation
# customers
# geolocation
# order_items
# order_payments
# order_reviews
# orders
# products
# sellers

# ROW COUNTS
# ========================================
# customers                 99,441
# sellers                   3,095
# products                  32,951
# category_translation      71
# orders                    99,441
# order_items               112,650
# order_payments            103,886
# order_reviews             99,224
# geolocation               1,000,163