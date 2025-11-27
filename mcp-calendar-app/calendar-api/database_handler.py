import sqlite3
import os

class DatabaseHandler:
    def __init__(self, db_name: str, check_same_thread: bool = True):
        self.db_name = db_name
        # If db_name is already a full path (contains /), use it as-is
        # Otherwise, append .db extension
        if '/' in db_name or db_name.endswith('.db'):
            db_path = db_name
        else:
            db_path = f'{db_name}.db'

        # Ensure the directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=check_same_thread)
        self.c = self.conn.cursor()

    def execute(self, cmd: str, params=()):
        try:
            self.c.execute(cmd, params)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

    def create_table(self, table_name: str, columns: dict):
        columns_str = ', '.join([f"{k} {v}" for k, v in columns.items()])
        cmd = f'CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})'
        self.execute(cmd)

    def insert_data(self, table_name: str, columns: dict, data: dict):
        placeholders = ', '.join('?' for _ in data)
        cmd = f'INSERT INTO {table_name} ({", ".join(data.keys())}) VALUES ({placeholders})'
        self.execute(cmd, tuple(data.values()))

    def update_data(self, table_name: str, data: dict, condition: dict):
        data_str = ', '.join([f"{k} = ?" for k in data.keys()])
        cond_str = ' AND '.join([f"{k} = ?" for k in condition.keys()])
        cmd = f'UPDATE {table_name} SET {data_str} WHERE {cond_str}'
        self.execute(cmd, tuple(data.values()) + tuple(condition.values()))

    def delete_data(self, table_name: str, condition: dict):
        cond_str = ' AND '.join([f"{k} = ?" for k in condition.keys()])
        cmd = f'DELETE FROM {table_name} WHERE {cond_str}'
        self.execute(cmd, tuple(condition.values()))

    def fetch_data(self, table_name: str, condition: dict = None):
        if condition:
            cond_str = ' AND '.join([f"{k} = ?" for k in condition.keys()])
            cmd = f'SELECT * FROM {table_name} WHERE {cond_str}'
            self.execute(cmd, tuple(condition.values()))
        else:
            cmd = f'SELECT * FROM {table_name}'
            self.execute(cmd)
        
        # Get column names
        columns = [description[0] for description in self.c.description] if self.c.description else []
        rows = self.c.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for row in rows:
            result.append(dict(zip(columns, row)))
        return result

    def check_existence(self, table_name: str, condition: dict):
        result = self.fetch_data(table_name, condition)
        return bool(result)

if __name__ == '__main__':
    dbh = DatabaseHandler(db_name="CalendarDB")
    print(dbh.check_existence(
        'calendar',
        {"sid": "TEXT", "name": "TEXT", "content": "TEXT", "category": "TEXT", "level": "INTEGER",
         "status": "REAL", "creation_time": "TEXT", "start_time": "TEXT", "end_time": "TEXT"},
        {"sid": "22"}
    ))
