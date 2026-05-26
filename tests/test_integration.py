from jirabot.vector_db import VectorDB
import os

def test_integration_vector_db_and_kb():
    kb_path = os.path.join(os.path.dirname(__file__), '../kb_data/sample_kb.json')
    db = VectorDB(kb_path)
    # Query for each KB entry
    for item in db.data:
        results = db.query(item['question'], top_k=1)
        assert results, f"No result for: {item['question']}"
        assert results[0]['answer'] == item['answer']
