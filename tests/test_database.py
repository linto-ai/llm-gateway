import unittest  # Instead of pytest for unittest
from app.model import Database

class TestDatabase(unittest.TestCase):
    def test_insert_and_retrieve(self):
        db = Database("/home/mkeita/llm-gateway/data/results.sqlite")
        task_id = "test-task-id"
        expected_result = "Test result content"

        db.put(task_id, expected_result)  # Insert test data
        
        retrieved_result = db.get(task_id)  # Retrieve the test data
        
        self.assertEqual(retrieved_result, expected_result, "Retrieved data doesn't match expected content")
