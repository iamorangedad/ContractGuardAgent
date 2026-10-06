import logging
import time
import uuid
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from typing import Optional

from app.config import get_config
from app.models.schemas import ContractUpload, ContractTask, ReviewSubmit, TaskStatus
from app.rag.db import get_task, save_task, update_task_status
from app.services.documents import extract_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

MAX_TEXT_CHARS = 500_000


def _task_config() -> dict:
    return get_config().get("task", {})


def _new_task(contract: ContractUpload) -> str:
    _validate_contract_text(contract.original_text, contract.modified_text)
    task_id = str(uuid.uuid4())
    save_task(task_id, {
        "task_id": task_id,
        "status": "pending",
        "original_text": contract.original_text,
        "modified_text": contract.modified_text,
        "category": contract.category,
        "differences": [],
        "evaluations": [],
        "human_reviews": [],
        "final_report": None,
        "error": None,
    })
    logger.info("Task %s created", task_id)
    return task_id


def _validate_contract_text(original_text: str, modified_text: str):
    if not original_text or not modified_text:
        raise HTTPException(status_code=400, detail="请提供合同原件和修改件")
    if len(original_text) > MAX_TEXT_CHARS or len(modified_text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=400, detail="合同文本超过 50 万字")


def _persist_result(task_id: str, result: dict):
    update_task_status(
        task_id,
        result["status"],
        differences=result.get("differences", []),
        evaluations=result.get("evaluations", []),
        human_reviews=result.get("human_reviews", []),
        final_report=result.get("final_report"),
        error=result.get("error"),
    )


def execute_review(task_id: str, original_text: str, modified_text: str, category: Optional[str], attempt: int = 0):
    from app.graph.workflow import run_contract_review

    task_cfg = _task_config()
    max_retries = int(task_cfg.get("max_retries", 3))
    retry_delay = float(task_cfg.get("retry_delay", 2))

    try:
        update_task_status(task_id, "in_progress")
        logger.info("Task %s started (attempt %s)", task_id, attempt + 1)
        result = run_contract_review(
            task_id=task_id,
            original_text=original_text,
            modified_text=modified_text,
            category=category or "",
        )
        _persist_result(task_id, result)
        logger.info("Task %s stopped at status %s", task_id, result["status"])
    except ValueError as exc:
        logger.error("Task %s rejected: %s", task_id, exc)
        update_task_status(task_id, "failed", error=str(exc))
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            execute_review(task_id, original_text, modified_text, category, attempt + 1)
        else:
            update_task_status(task_id, "failed", error=str(exc))


@router.post("/compare", response_model=TaskStatus)
async def compare_contracts(contract: ContractUpload, background_tasks: BackgroundTasks):
    task_id = _new_task(contract)
    background_tasks.add_task(
        execute_review,
        task_id,
        contract.original_text,
        contract.modified_text,
        contract.category,
    )
    return TaskStatus(task_id=task_id, status="pending", message="任务已创建，正在处理中")


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        message=get_status_message(task["status"]),
    )


def get_status_message(status: str) -> str:
    messages = {
        "pending": "任务等待中",
        "in_progress": "正在分析合同...",
        "waiting_human": "需要法务人工确认",
        "completed": "审查完成",
        "failed": "处理失败",
    }
    return messages.get(status, "未知状态")


@router.get("/result/{task_id}", response_model=ContractTask)
async def get_task_result(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return ContractTask(**task)


@router.post("/retry/{task_id}")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    update_task_status(task_id, "pending", error=None)
    background_tasks.add_task(
        execute_review,
        task_id,
        task["original_text"],
        task["modified_text"],
        task.get("category"),
    )
    return {"message": "Task retry initiated", "task_id": task_id}


@router.post("/review")
async def submit_human_review(review: ReviewSubmit):
    from app.graph.workflow import resume_contract_review

    task = get_task(review.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "waiting_human":
        raise HTTPException(status_code=400, detail="Task is not waiting for human review")

    reviews_list = [
        {
            "evaluation_id": item.evaluation_id,
            "approved": item.approved,
            "modified_suggestion": item.modified_suggestion,
            "comment": item.comment,
        }
        for item in review.reviews
    ]
    update_task_status(review.task_id, "in_progress", human_reviews=reviews_list)
    logger.info("Human review submitted for task %s", review.task_id)

    try:
        result = await asyncio.to_thread(resume_contract_review, review.task_id, reviews_list)
    except ValueError as exc:
        update_task_status(review.task_id, "waiting_human", human_reviews=reviews_list, error=str(exc))
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.exception("Resume failed for task %s", review.task_id)
        update_task_status(review.task_id, "failed", error=str(exc))
        raise HTTPException(status_code=500, detail="恢复审核失败")

    _persist_result(review.task_id, result)
    return {"message": "Review submitted successfully", "task_id": review.task_id, "status": result["status"]}


@router.post("/upload")
async def upload_contracts(
    background_tasks: BackgroundTasks,
    original_file: Optional[UploadFile] = File(None),
    modified_file: Optional[UploadFile] = File(None),
    category: Optional[str] = Form(None),
):
    if original_file is None or modified_file is None:
        raise HTTPException(status_code=400, detail="请提供两个合同文件")

    try:
        original_text = extract_text(original_file.filename or "", await original_file.read())
        modified_text = extract_text(modified_file.filename or "", await modified_file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    contract = ContractUpload(
        original_text=original_text,
        modified_text=modified_text,
        category=category,
    )
    task_id = _new_task(contract)
    background_tasks.add_task(
        execute_review,
        task_id,
        contract.original_text,
        contract.modified_text,
        contract.category,
    )
    return TaskStatus(task_id=task_id, status="pending", message="任务已创建，正在处理中")
