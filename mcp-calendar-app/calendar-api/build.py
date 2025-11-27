import os
import configparser
import json
import sqlite3
import database_handler

def load_config(file_path):
    config = configparser.ConfigParser()
    config.read(file_path)
    return config['DEFAULT']

def get_db_path():
    """Get database path from environment variable or config"""
    db_path = os.getenv('DATABASE_PATH')
    if db_path:
        # Remove .db extension if present in the path
        return db_path.replace('.db', '')
    else:
        info = load_config('db.conf')
        return info['db_name']

def build_db():
    info = load_config('db.conf')
    db_name = get_db_path()
    table_name = info.get('table_name')
    columns = json.loads(info.get('columns', '{}'))

    if not table_name or not columns:
        raise ValueError("Database configuration is incomplete.")

    # Construct the full path
    if '/' in db_name or db_name.endswith('.db'):
        db_path = db_name if db_name.endswith('.db') else f"{db_name}.db"
    else:
        db_path = f"{db_name}.db"

    # Check if the database file already exists
    if os.path.exists(db_path):
        print(f"Database file '{db_path}' already exists.")
        dbh = database_handler.DatabaseHandler(db_name=db_name)
        
        # Check if the table exists
        try:
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            table_exists = cursor.fetchone()[0] == 1
            connection.close()

            if table_exists:
                print(f"Table '{table_name}' already exists. No action needed.")
                return
            else:
                print(f"Table '{table_name}' does not exist. Creating table...")
                dbh.create_table(table_name=table_name, columns=columns)

        except Exception as e:
            print(f"An error occurred while checking the table existence: {e}")
            raise

    else:
        print(f"Database file '{db_path}' does not exist. Creating database and table...")
        dbh = database_handler.DatabaseHandler(db_name=db_name)
        dbh.create_table(table_name=table_name, columns=columns)

if __name__ == '__main__':
    build_db()
