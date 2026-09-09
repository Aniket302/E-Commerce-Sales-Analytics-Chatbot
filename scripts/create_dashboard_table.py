import sqlite3


DB_PATH = "database/olist.db"


def main():
    connection = sqlite3.connect(DB_PATH)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS pinned_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            chart_json TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_refreshed_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

    print("pinned_charts table created successfully.")


if __name__ == "__main__":
    main()