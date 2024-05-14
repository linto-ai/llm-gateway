import sqlite3
import logging

# Setup logging configuration
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)

class Database:
    def __init__(self, db_path="path_to_results.sqlite"):
        self.db_path = db_path
        self.init_db()  # Initialize the database
        logging.info("Database initialized successfully.")  # Log successful initialization

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)  # Establish connection
        logging.info("Database connection established.")  # Log successful connection
        return conn

    def init_db(self):
        conn = self.get_conn()  # Get a connection
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS results
                               (task_id TEXT PRIMARY KEY, result TEXT)''')
        conn.commit()  # Commit the changes
        conn.close()  # Close the connection
        logging.info("Database table 'results' created or verified.")  # Log successful table creation

    def put(self, task_id, result):
        conn = self.get_conn()  # Get a connection
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO results (task_id, result) VALUES (?, ?)", 
                            (str(task_id), str(result)))
        conn.commit()  # Commit the changes
        conn.close()
        logging.info(f"Inserted or updated result for task_id {task_id}.")  # Log successful insert/update

    def get(self, task_id):
        conn = self.get_conn()  # Get a connection
        cursor = conn.cursor()
        cursor.execute("SELECT result FROM results WHERE task_id=?", (str(task_id),))
        result = cursor.fetchone()  # Fetch the result
        conn.close()
        if result:
            logging.info(f"Data retrieved for task_id {task_id}: {result[0]}")
            return result[0]  # Return the first item in the fetched row
        else:
            logging.warning(f"No data found for task_id {task_id}.")
            return None


