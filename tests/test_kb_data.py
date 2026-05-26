import json
import os

def test_kb_data_load():
    kb_path = os.path.join(os.path.dirname(__file__), '../kb_data/sample_kb.json')
    with open(kb_path, 'r') as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert all('question' in item and 'answer' in item for item in data)
    assert len(data) >= 3
