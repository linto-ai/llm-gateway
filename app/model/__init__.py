import plyvel

class Database:
    def __init__(self, db_path='/tmp/testdb/'):
        self.db_path = db_path

    def put(self, task_id, result):
        db = plyvel.DB(self.db_path, create_if_missing=True)
        db.put(str(task_id).encode('utf-8'), str(result).encode('utf-8'))
        db.close()

    def get(self, task_id):
        db = plyvel.DB(self.db_path, create_if_missing=True)
        result = db.get(str(task_id).encode('utf-8'))
        db.close()
        return result