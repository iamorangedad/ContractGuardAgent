import difflib
import logging
from typing import Any, Dict, List

from langgraph.types import interrupt

from app.config import get_config
from app.graph.state import ContractReviewState
from app.rag.retriever import retriever
from app.services.report import build_structured_report

logger = logging.getLogger(__name__)

_RISK_LEVELS = {
    "green": "green",
    "yellow": "yellow",
    "red": "red",
    "绿色": "green",
    "黄色": "yellow",
    "红色": "red",
}


def normalize_risk(level: str) -> str:
    return _RISK_LEVELS.get((level or "").strip(), "yellow")


def node_retriever(state: ContractReviewState) -> ContractReviewState:
    state["status"] = "in_progress"
    category = state.get("category") or ""
    retrieval_result = retriever.retrieve_for_contract(state["modified_text"], category)
    state["retrieved_templates"] = retrieval_result["templates"]
    state["playbook_rules"] = retrieval_result["playbook_rules"]
    return state


def node_analyzer(state: ContractReviewState) -> ContractReviewState:
    original_lines = [line.strip() for line in state["original_text"].split("\n") if line.strip()]
    modified_lines = [line.strip() for line in state["modified_text"].split("\n") if line.strip()]

    differences = []
    matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            original_span = original_lines[i1:i2]
            modified_span = modified_lines[j1:j2]
            for i in range(max(len(original_span), len(modified_span))):
                orig = original_span[i] if i < len(original_span) else ""
                mod = modified_span[i] if i < len(modified_span) else ""
                if orig or mod:
                    differences.append({
                        "original_section": orig,
                        "modified_section": mod,
                        "similarity": difflib.SequenceMatcher(None, orig, mod).ratio(),
                        "change_type": "modified",
                    })
        elif tag == "delete":
            for orig in original_lines[i1:i2]:
                differences.append({
                    "original_section": orig,
                    "modified_section": "",
                    "similarity": 0.0,
                    "change_type": "removed",
                })
        elif tag == "insert":
            for mod in modified_lines[j1:j2]:
                differences.append({
                    "original_section": "",
                    "modified_section": mod,
                    "similarity": 0.0,
                    "change_type": "added",
                })

    significant = [
        item for item in differences
        if len(item["modified_section"]) > 10 or len(item["original_section"]) > 10
    ]
    state["differences"] = significant if significant else differences[:10]
    return state


def node_evaluator(state: ContractReviewState) -> ContractReviewState:
    differences = state.get("differences", [])
    playbook_rules = state.get("playbook_rules", [])
    templates = state.get("retrieved_templates", [])
    use_llm = bool(get_config().get("llm", {}).get("use_llm", False))
    evaluations = []

    for idx, diff in enumerate(differences):
        evaluations.append(_evaluate_difference(idx, diff, playbook_rules, templates, use_llm))

    state["evaluations"] = evaluations
    has_risk = any(item["risk_level"] in ("yellow", "red") for item in evaluations)
    state["needs_human_review"] = has_risk
    state["status"] = "waiting_human" if has_risk else "in_progress"
    state["continue_review"] = False
    return state


def node_human_loop(state: ContractReviewState) -> dict:
    pending = [
        {
            "id": item.get("id"),
            "risk_level": item.get("risk_level"),
            "suggestion": item.get("suggestion"),
            "explanation": item.get("explanation"),
        }
        for item in state.get("evaluations", [])
        if item.get("risk_level") in ("yellow", "red")
    ]
    reviews = interrupt({"task_id": state.get("task_id"), "pending": pending})
    if not isinstance(reviews, list):
        raise ValueError("人工审核结果必须是列表")

    normalized = []
    for review in reviews:
        if not isinstance(review, dict) or "evaluation_id" not in review:
            raise ValueError("审核意见缺少 evaluation_id")
        normalized.append({
            "evaluation_id": review.get("evaluation_id"),
            "approved": bool(review.get("approved")),
            "modified_suggestion": review.get("modified_suggestion"),
            "comment": review.get("comment"),
        })

    return {
        "human_reviews": normalized,
        "review_round": state.get("review_round", 0) + 1,
        "continue_review": False,
        "needs_human_review": False,
        "status": "in_progress",
    }


def node_finalizer(state: ContractReviewState) -> ContractReviewState:
    evaluations = state.get("evaluations", [])
    human_reviews = state.get("human_reviews", [])
    report = build_structured_report(evaluations, human_reviews)

    if evaluations and bool(get_config().get("llm", {}).get("use_llm", False)):
        try:
            from app.services.llm import get_llm_service
            report = get_llm_service().generate_final_report(evaluations, human_reviews)
        except Exception:
            logger.exception("模型生成最终报告失败，改用结构化报告")

    state["final_report"] = report
    state["status"] = "completed"
    return state


def _evaluate_difference(
    idx: int,
    diff: Dict[str, Any],
    playbook_rules: List[Dict[str, Any]],
    templates: List[Dict[str, Any]],
    use_llm: bool,
) -> Dict[str, Any]:
    modified_text = diff.get("modified_section", "")
    original_text = diff.get("original_section", "")
    change_type = diff.get("change_type", "modified")
    reference_templates = [item.get("title") for item in templates[:2] if item.get("title")]

    if use_llm:
        try:
            from app.services.llm import get_llm_service
            llm_result = get_llm_service().analyze_contract_difference(
                original_section=original_text,
                modified_section=modified_text,
                change_type=change_type,
                playbook_rules=playbook_rules,
                templates=templates,
            )
            return {
                "id": idx,
                "difference": diff,
                "risk_level": normalize_risk(llm_result["risk_level"]),
                "matched_rule": llm_result.get("matched_rule"),
                "suggestion": llm_result["suggestion"],
                "explanation": llm_result["explanation"],
                "reference_templates": reference_templates,
            }
        except Exception:
            logger.exception("模型评估条款失败，改用规则")

    matched_rule, suggestion, explanation, risk_level = _match_rule(
        original_text, modified_text, diff, playbook_rules
    )
    if reference_templates:
        explanation = f"{explanation}（参考模板：{'、'.join(reference_templates)}）"

    return {
        "id": idx,
        "difference": diff,
        "risk_level": risk_level,
        "matched_rule": matched_rule,
        "suggestion": suggestion,
        "explanation": explanation,
        "reference_templates": reference_templates,
    }


def _match_rule(original_text: str, modified_text: str, diff: Dict[str, Any], playbook_rules: List[Dict[str, Any]]):
    best_match_rule = None
    best_score = 0
    text_to_check = f"{modified_text} {original_text}".lower()

    for rule in playbook_rules:
        keywords = (rule.get("keywords") or "").lower()
        score = 0
        if keywords:
            for keyword in [item.strip() for item in keywords.split(",") if item.strip()]:
                if keyword in text_to_check:
                    score += 1
        if score > best_score:
            best_score = score
            best_match_rule = rule

    if best_match_rule and best_score > 0:
        return (
            best_match_rule,
            best_match_rule["action"],
            best_match_rule["description"],
            normalize_risk(best_match_rule["risk_level"]),
        )

    if diff.get("change_type") == "added":
        return None, "请确认此新增条款是否符合公司标准", "新增条款，未匹配到明确的合规规则", "yellow"
    if diff.get("change_type") == "removed":
        return None, "请确认删除此条款的原因", "删除了原有条款", "yellow"
    if diff.get("similarity", 1.0) > 0.8:
        return None, "符合标准", "修改内容与原文高度相似，无明显风险", "green"
    return None, "请人工审核此修改", "修改内容较复杂，建议人工确认", "yellow"
