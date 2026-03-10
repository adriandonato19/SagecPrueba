
import os
import sys

# Define base directory (assuming script is in /scripts/ and project root is one level up)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')

def delete_database():
    print(f"Looking for database at: {DB_PATH}")
    
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"Successfully deleted {DB_PATH}")
            print("All data and tables have been removed.")
        except PermissionError:
            print(f"Error: Could not delete {DB_PATH}. The file might be in use.")
            print("Please stop the server (Ctrl+C) and try again.")
    else:
        print(f"No database found at {DB_PATH}")

if __name__ == "__main__":
    delete_database()
