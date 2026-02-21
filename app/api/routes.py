import uuid
import asyncio
from typing import Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import ContractUpload, ContractTask, TaskStatus, ReviewSubmit

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

tasks_store: Dict[str, Dict] = {}

@router.post("/compare", response_model=TaskStatus)
async def compare_contracts(contract: ContractUpload):
    task_id = str(uuid.uuid4())
    
    tasks_store[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "original_text": contract.original_text,
        "modified_text": contract.modified_text,
        "category": contract.category,
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "final_report": None,
        "created_at": None
    }
    
    asyncio.create_task(run_review_task(task_id, contract))
    
    return TaskStatus(
        task_id=task_id,
        status="pending",
        message="任务已创建，正在处理中"
    )

async def run_review_task(task_id: str, contract: ContractUpload):
    from app.graph.workflow import run_contract_review
    from app.rag.db import init_db
    
    init_db()
    
    try:
        tasks_store[task_id]["status"] = "in_progress"
        
        result = run_contract_review(
            task_id=task_id,
            original_text=contract.original_text,
            modified_text=contract.modified_text,
            category=contract.category
        )
        
        tasks_store[task_id]["status"] = result["status"]
        tasks_store[task_id]["differences"] = result.get("differences", [])
        tasks_store[task_id]["evaluations"] = result.get("evaluations", [])
        tasks_store[task_id]["human_reviews"] = result.get("human_reviews", [])
        tasks_store[task_id]["final_report"] = result.get("final_report")
        
    except Exception as e:
        tasks_store[task_id]["status"] = "failed"
        tasks_store[task_id]["error"] = str(e)

@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_store[task_id]
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        message=get_status_message(task["status"])
    )

def get_status_message(status: str) -> str:
    messages = {
        "pending": "任务等待中",
        "in_progress": "正在分析合同...",
        "waiting_human": "需要法务人工确认",
        "completed": "审查完成",
        "failed": "处理失败"
    }
    return messages.get(status, "未知状态")

@router.get("/result/{task_id}", response_model=ContractTask)
async def get_task_result(task_id: str):
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_store[task_id]
    return ContractTask(**task)

@router.post("/review")
async def submit_human_review(review: ReviewSubmit):
    if review.task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_store[review.task_id]
    
    if task["status"] != "waiting_human":
        raise HTTPException(status_code=400, detail="Task is not waiting for human review")
    
    reviews_list = []
    for r in review.reviews:
        reviews_list.append({
            "evaluation_id": r.evaluation_id,
            "approved": r.approved,
            "modified_suggestion": r.modified_suggestion,
            "comment": r.comment
        })
    
    task["human_reviews"] = reviews_list
    
    from app.graph.workflow import run_contract_review
    
    result = run_contract_review(
        task_id=task["task_id"],
        original_text=task["original_text"],
        modified_text=task["modified_text"],
        category=task.get("category")
    )
    
    task["status"] = result["status"]
    task["final_report"] = result.get("final_report")
    
    return {"message": "Review submitted successfully", "task_id": review.task_id}
