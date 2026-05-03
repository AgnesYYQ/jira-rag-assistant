import pytest
import sys
from jirabot import main

def test_main_dry_run(monkeypatch):
    # Patch sys.argv and print to capture output
    monkeypatch.setattr(sys, 'argv', ['main.py', '--ticket', 'ABC-123', '--dry-run'])
    monkeypatch.setattr('builtins.print', lambda *a, **k: None)
    try:
        main.main()
    except SystemExit:
        pass  # argparse exits
