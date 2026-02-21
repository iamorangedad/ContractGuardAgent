import re
import difflib
from typing import List, Dict, Any
from app.graph.state import ContractReviewState
from app.rag.retriever import retriever
from app.models.schemas import ReviewStatus

def node_retriever(state: ContractReviewState) -> ContractReviewState:
    state["status"] = "in_progress"
    
    modified_text = state["modified_text"]
    category = state.get("category") or None
    
    retrieval_result = retriever.retrieve_for_contract(modified_text, category or "")
    
    state["retrieved_templates"] = retrieval_result["templates"]
    state["playbook_rules"] = retrieval_result["playbook_rules"]
    
    return state

def node_analyzer(state: ContractReviewState) -> ContractReviewState:
    original = state["original_text"]
    modified = state["modified_text"]
    
    original_lines = [line.strip() for line in original.split('\n') if line.strip()]
    modified_lines = [line.strip() for line in modified.split('\n') if line.strip()]
    
    differences = []
    
    matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            for i in range(max(len(original_lines[i1:i2]), len(modified_lines[j1:j2]))):
                orig = original_lines[i1 + i] if i < len(original_lines[i1:i2]) else ""
                mod = modified_lines[j1 + i] if i < len(modified_lines[j1:j2]) else ""
                if orig or mod:
                    similarity = difflib.SequenceMatcher(None, orig, mod).ratio()
                    differences.append({
                        "original_section": orig,
                        "modified_section": mod,
                        "similarity": similarity,
                        "change_type": "modified"
                    })
        elif tag == 'delete':
            for orig in original_lines[i1:i2]:
                differences.append({
                    "original_section": orig,
                    "modified_section": "",
                    "similarity": 0.0,
                    "change_type": "removed"
                })
        elif tag == 'insert':
            for mod in modified_lines[j1:j2]:
                differences.append({
                    "original_section": "",
                    "modified_section": mod,
                    "similarity": 0.0,
                    "change_type": "added"
                })
    
    significant_diffs = [d for d in differences if len(d["modified_section"]) > 10 or len(d["original_section"]) > 10]
    
    state["differences"] = significant_diffs if significant_diffs else differences[:10]
    
    return state

def node_evaluator(state: ContractReviewState) -> ContractReviewState:
    differences = state.get("differences", [])
    playbook_rules = state.get("playbook_rules", [])
    
    evaluations = []
    
    for idx, diff in enumerate(differences):
        modified_text = diff.get("modified_section", "")
        original_text = diff.get("original_section", "")
        
        best_match_rule = None
        best_score = 0
        
        for rule in playbook_rules:
            keywords = rule.get("keywords", "").lower()
            rule_desc = rule.get("description", "").lower()
            
            text_to_check = (modified_text + " " + original_text).lower()
            
            score = 0
            if keywords:
                keyword_list = [k.strip() for k in keywords.split(",")]
                for kw in keyword_list:
                    if kw in text_to_check:
                        score += 1
                    if kw in rule_desc:
                        score += 0.5
            
            if score > best_score:
                best_score = score
                best_match_rule = rule
        
        if best_match_rule and best_score > 0:
            risk_level = best_match_rule["risk_level"]
            suggestion = best_match_rule["action"]
            explanation = best_match_rule["description"]
        else:
            if diff.get("change_type") == "added":
                risk_level = "yellow"
                suggestion = "请确认此新增条款是否符合公司标准"
                explanation = "新增条款，未匹配到明确的合规规则"
            elif diff.get("change_type") == "removed":
                risk_level = "yellow"
                suggestion = "请确认删除此条款的原因"
                explanation = "删除了原有条款"
            else:
                similarity = diff.get("similarity", 1.0)
                if similarity > 0.8:
                    risk_level = "green"
                    suggestion = "符合标准"
                    explanation = "修改内容与原文高度相似，无明显风险"
                else:
                    risk_level = "yellow"
                    suggestion = "请人工审核此修改"
                    explanation = "修改内容较复杂，建议人工确认"
        
        evaluations.append({
            "id": idx,
            "difference": diff,
            "risk_level": risk_level,
            "matched_rule": best_match_rule,
            "suggestion": suggestion,
            "explanation": explanation
        })
    
    state["evaluations"] = evaluations
    
    has_yellow_or_red = any(e["risk_level"] in ["yellow", "red"] for e in evaluations)
    state["needs_human_review"] = has_yellow_or_red
    
    if has_yellow_or_red:
        state["status"] = "waiting_human"
    else:
        state["status"] = "in_progress"
    
    return state

def node_human_loop(state: ContractReviewState) -> ContractReviewState:
    return state

def node_finalizer(state: ContractReviewState) -> ContractReviewState:
    evaluations = state.get("evaluations", [])
    human_reviews = state.get("human_reviews", [])
    
    review_map = {r["evaluation_id"]: r for r in human_reviews}
    
    report_lines = ["# 合同对比审查报告", ""]
    
    green_items = [e for e in evaluations if e["risk_level"] == "green"]
    yellow_items = [e for e in evaluations if e["risk_level"] == "yellow"]
    red_items = [e for e in evaluations if e["risk_level"] == "red"]
    
    report_lines.append(f"## 审查摘要")
    report_lines.append(f"- 绿色（通过）: {len(green_items)} 项")
    report_lines.append(f"- 黄色（需确认）: {len(yellow_items)} 项")
    report_lines.append(f"- 红色（不可接受）: {len(red_items)} 项")
    report_lines.append("")
    
    if green_items:
        report_lines.append("## 绿色项（符合标准）")
        for item in green_items:
            report_lines.append(f"- {item['explanation']}")
            report_lines.append(f"  原文: {item['difference'].get('original_section', '')[:100]}...")
            report_lines.append(f"  修改: {item['difference'].get('modified_section', '')[:100]}...")
        report_lines.append("")
    
    if yellow_items:
        report_lines.append("## 黄色项（需人工确认）")
        for item in yellow_items:
            review = review_map.get(item["id"], {})
            approved = review.get("approved", False)
            status = "已批准" if approved else "待确认"
            suggestion = review.get("modified_suggestion", item["suggestion"])
            
            report_lines.append(f"- [{status}] {item['explanation']}")
            report_lines.append(f"  建议: {suggestion}")
            if review.get("comment"):
                report_lines.append(f"  法务意见: {review['comment']}")
        report_lines.append("")
    
    if red_items:
        report_lines.append("## 红色项（违反合规）")
        for item in red_items:
            review = review_map.get(item["id"], {})
            approved = review.get("approved", False)
            status = "已批准" if approved else "待确认"
            suggestion = review.get("modified_suggestion", item["suggestion"])
            
            report_lines.append(f"- [{status}] {item['explanation']}")
            report_lines.append(f"  风险: {item['matched_rule'].get('description', '') if item.get('matched_rule') else '高风险条款'}")
            report_lines.append(f"  建议: {suggestion}")
            if review.get("comment"):
                report_lines.append(f"  法务意见: {review['comment']}")
        report_lines.append("")
    
    report_lines.append("## 最终建议")
    
    if red_items:
        unapproved_red = [r for r in human_reviews if r["evaluation_id"] in [e["id"] for e in red_items] and not r.get("approved")]
        if unapproved_red:
            report_lines.append("存在未批准的红色风险项，建议与合同对方协商修改后再签约。")
        else:
            report_lines.append("红色风险项已全部得到法务确认，但建议谨慎处理。")
    else:
        report_lines.append("合同经审查未发现重大合规风险，可以继续流程。")
    
    state["final_report"] = "\n".join(report_lines)
    state["status"] = "completed"
    
    return state
