import sqlite3

class Database:
    def __init__(self, db_path='/tmp/resultDB.sqlite'):
        self.db_path = db_path
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        return conn

    def init_db(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS results
                               (task_id text primary key, result text)''')
        conn.commit()
        conn.close()

    def put(self, task_id, result):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO results VALUES (?,?)", 
                            (str(task_id), str(result)))
        conn.commit()
        conn.close()

    def get(self, task_id):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT result FROM results WHERE task_id=?", (str(task_id),))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None