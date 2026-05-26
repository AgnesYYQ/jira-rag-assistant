import os
import pytest
from jirabot.vector_db import VectorDB

KB_PATH = os.path.join(os.path.dirname(__file__), '../kb_data/sample_kb.json')

def test_vector_db_query():
    db = VectorDB(KB_PATH)
    results = db.query('reset password', top_k=2)
    assert any('password' in r['question'] for r in results)
    results = db.query('create issue', top_k=2)
    assert any('create' in r['question'] for r in results)
    results = db.query('assign', top_k=2)
    assert any('assign' in r['question'] for r in results)
