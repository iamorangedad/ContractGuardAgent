import pytest
import os
import tempfile
from app.rag import db

TEST_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db")

@pytest.fixture
def test_db():
    original_db_path = db.DB_PATH
    db.DB_PATH = TEST_DB.name
    db.init_db()
    yield
    db.DB_PATH = original_db_path
    os.unlink(TEST_DB.name)

def test_init_db(test_db):
    assert os.path.exists(db.DB_PATH)

def test_save_and_get_task(test_db):
    task_data = {
        "task_id": "test-123",
        "status": "pending",
        "original_text": "原始合同",
        "modified_text": "修改后合同",
        "category": "采购",
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "final_report": None,
        "error": None
    }
    
    db.save_task("test-123", task_data)
    task = db.get_task("test-123")
    
    assert task is not None
    assert task["task_id"] == "test-123"
    assert task["status"] == "pending"

def test_update_task_status(test_db):
    task_data = {
        "task_id": "test-456",
        "status": "pending",
        "original_text": "原始合同",
        "modified_text": "修改后合同",
        "category": None,
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "final_report": None,
        "error": None
    }
    
    db.save_task("test-456", task_data)
    db.update_task_status("test-456", "in_progress")
    
    task = db.get_task("test-456")
    assert task["status"] == "in_progress"

def test_get_nonexistent_task(test_db):
    task = db.get_task("nonexistent")
    assert task is None
