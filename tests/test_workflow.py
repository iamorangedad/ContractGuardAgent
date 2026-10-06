import pytest
from fastapi.testclient import TestClient

from app.graph.workflow import reset_graph, resume_contract_review, run_contract_review
from app.main import app
from app.rag import db
from app.rag.db import init_db

ORIGINAL = "第一条 合同金额为人民币100万元，按原约定执行。"
MODIFIED = "第一条 本合同新增一条需要确认的付款安排条款，请法务审核。"


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.delenv("USE_LLM", raising=False)
    monkeypatch.delenv("USE_EMBEDDINGS", raising=False)
    db.DB_PATH = str(tmp_path / "contracts.db")
    reset_graph()
    init_db()
    yield
    reset_graph()
    db.DB_PATH = None


def test_identical_contract_completes_without_human(isolated_db):
    text = "产品质量符合国家标准，质保期为十二个月。"
    result = run_contract_review("same-text", text, text, "采购")
    assert result["status"] == "completed"
    assert "未发现重大合规风险" in result["final_report"]


def test_risk_pauses_and_survives_restart(isolated_db):
    result = run_contract_review("task-hitl", ORIGINAL, MODIFIED, "采购")
    assert result["status"] == "waiting_human"
    assert result["evaluations"]
    assert any(item["risk_level"] in ("yellow", "red") for item in result["evaluations"])
    assert "reference_templates" in result["evaluations"][0]

    reset_graph()

    evaluation_id = next(
        item["id"] for item in result["evaluations"] if item["risk_level"] in ("yellow", "red")
    )
    resumed = resume_contract_review("task-hitl", [{
        "evaluation_id": evaluation_id,
        "approved": False,
        "comment": "请改回本地法院",
        "modified_suggestion": "提交本地法院管辖",
    }])
    assert resumed["status"] == "completed"
    assert "请改回本地法院" in resumed["final_report"]
    assert "已拒绝" in resumed["final_report"]


def test_api_review_round_trip(isolated_db):
    client = TestClient(app)
    created = client.post("/api/contracts/compare", json={
        "original_text": ORIGINAL,
        "modified_text": MODIFIED,
        "category": "采购",
    })
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    status = client.get(f"/api/contracts/status/{task_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "waiting_human"

    result = client.get(f"/api/contracts/result/{task_id}").json()
    reviews = [
        {
            "evaluation_id": item["id"],
            "approved": True,
            "comment": "同意该修改",
            "modified_suggestion": item.get("suggestion"),
        }
        for item in result["evaluations"]
        if item["risk_level"] in ("yellow", "red")
    ]
    submitted = client.post("/api/contracts/review", json={"task_id": task_id, "reviews": reviews})
    assert submitted.status_code == 200

    final = client.get(f"/api/contracts/result/{task_id}").json()
    assert final["status"] == "completed"
    assert "同意该修改" in final["final_report"]


def test_upload_docx(isolated_db):
    import io
    from docx import Document

    def docx_bytes(text):
        document = Document()
        document.add_paragraph(text)
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    client = TestClient(app)
    response = client.post(
        "/api/contracts/upload",
        data={"category": "采购"},
        files={
            "original_file": ("a.docx", docx_bytes(ORIGINAL), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "modified_file": ("b.docx", docx_bytes(MODIFIED), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    status = client.get(f"/api/contracts/status/{task_id}")
    assert status.json()["status"] == "waiting_human"


def test_health_reports_llm_disabled(isolated_db):
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["llm"]["status"] == "disabled"
    ready = client.get("/ready")
    assert ready.status_code == 200
