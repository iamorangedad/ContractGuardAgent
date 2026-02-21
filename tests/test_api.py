import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.rag.db import init_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_compare_contracts():
    payload = {
        "original_text": "合同金额：100元",
        "modified_text": "合同金额：200元",
        "category": "采购"
    }
    
    response = client.post("/api/contracts/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"

def test_get_task_status_not_found():
    response = client.get("/api/contracts/status/nonexistent")
    assert response.status_code == 404

def test_get_task_result_not_found():
    response = client.get("/api/contracts/result/nonexistent")
    assert response.status_code == 404
