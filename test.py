import unittest
from app.model import Database  # Adjust based on your project structure

class TestDatabase(unittest.TestCase):
    def test_insert_and_retrieve(self):
        db = Database("/home/mkeita/llm-gateway/data/results.sqlite")
        task_id = "test-task-id"
        expected_result = "Test result content"

        # Insert the test data
        db.put(task_id, expected_result)
        
        # Retrieve the test data
        retrieved_result = db.get(task_id)
        
        # Assert the retrieved data is as expected
        self.assertEqual(retrieved_result, expected_result, "Retrieved data doesn't match expected content")

if __name__ == "__main__":
    unittest.main()
