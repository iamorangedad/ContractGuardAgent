import uuid
import asyncio
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from app.models.schemas import ContractUpload, ContractTask, TaskStatus, ReviewSubmit
from app.rag.db import save_task, get_task, update_task_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

MAX_RETRIES = 3
RETRY_DELAY = 2

@router.post("/compare", response_model=TaskStatus)
async def compare_contracts(contract: ContractUpload):
    task_id = str(uuid.uuid4())
    
    task_data = {
        "task_id": task_id,
        "status": "pending",
        "original_text": contract.original_text,
        "modified_text": contract.modified_text,
        "category": contract.category,
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "final_report": None,
        "error": None
    }
    
    save_task(task_id, task_data)
    logger.info(f"Task {task_id} created")
    
    asyncio.create_task(run_review_task_with_retry(task_id, contract))
    
    return TaskStatus(
        task_id=task_id,
        status="pending",
        message="任务已创建，正在处理中"
    )

async def run_review_task_with_retry(task_id: str, contract: ContractUpload, retry_count: int = 0):
    from app.graph.workflow import run_contract_review
    
    try:
        update_task_status(task_id, "in_progress")
        logger.info(f"Task {task_id} started processing (attempt {retry_count + 1})")
        
        category = contract.category if contract.category else ""
        
        result = run_contract_review(
            task_id=task_id,
            original_text=contract.original_text,
            modified_text=contract.modified_text,
            category=category
        )
        
        update_task_status(
            task_id,
            result["status"],
            differences=result.get("differences", []),
            evaluations=result.get("evaluations", []),
            human_reviews=result.get("human_reviews", []),
            final_report=result.get("final_report")
        )
        logger.info(f"Task {task_id} completed with status: {result['status']}")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        
        if retry_count < MAX_RETRIES - 1:
            logger.info(f"Retrying task {task_id} in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
            await run_review_task_with_retry(task_id, contract, retry_count + 1)
        else:
            logger.error(f"Task {task_id} failed after {MAX_RETRIES} attempts")
            update_task_status(task_id, "failed", error=str(e))

@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task = get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
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
    task = get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return ContractTask(**task)

@router.post("/retry/{task_id}")
async def retry_task(task_id: str):
    task = get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")
    
    contract = ContractUpload(
        original_text=task["original_text"],
        modified_text=task["modified_text"],
        category=task.get("category")
    )
    
    update_task_status(task_id, "pending")
    asyncio.create_task(run_review_task_with_retry(task_id, contract))
    
    return {"message": "Task retry initiated", "task_id": task_id}

@router.post("/review")
async def submit_human_review(review: ReviewSubmit):
    task = get_task(review.task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
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
    
    update_task_status(review.task_id, "in_progress", human_reviews=reviews_list)
    logger.info(f"Human review submitted for task {review.task_id}")
    
    from app.graph.workflow import run_contract_review
    
    result = run_contract_review(
        task_id=task["task_id"],
        original_text=task["original_text"],
        modified_text=task["modified_text"],
        category=task.get("category") or ""
    )
    
    update_task_status(
        review.task_id,
        result["status"],
        final_report=result.get("final_report")
    )
    
    return {"message": "Review submitted successfully", "task_id": review.task_id}

@router.post("/upload")
async def upload_contracts(
    original_file: Optional[UploadFile] = File(None),
    modified_file: Optional[UploadFile] = File(None),
    category: Optional[str] = Form(None)
):
    original_text = ""
    modified_text = ""
    
    if original_file:
        content = await original_file.read()
        try:
            original_text = content.decode("utf-8")
        except UnicodeDecodeError:
            original_text = content.decode("gbk", errors="ignore")
    
    if modified_file:
        content = await modified_file.read()
        try:
            modified_text = content.decode("utf-8")
        except UnicodeDecodeError:
            modified_text = content.decode("gbk", errors="ignore")
    
    if not original_text or not modified_text:
        raise HTTPException(status_code=400, detail="请提供两个合同文件")
    
    contract = ContractUpload(
        original_text=original_text,
        modified_text=modified_text,
        category=category
    )
    
    task_id = str(uuid.uuid4())
    
    task_data = {
        "task_id": task_id,
        "status": "pending",
        "original_text": contract.original_text,
        "modified_text": contract.modified_text,
        "category": contract.category,
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "final_report": None,
        "error": None
    }
    
    save_task(task_id, task_data)
    logger.info(f"Task {task_id} created from file upload")
    
    asyncio.create_task(run_review_task_with_retry(task_id, contract))
    
    return TaskStatus(
        task_id=task_id,
        status="pending",
        message="任务已创建，正在处理中"
    )
