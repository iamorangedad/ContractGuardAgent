from typing import Any, Dict, List


def build_structured_report(
    evaluations: List[Dict[str, Any]],
    human_reviews: List[Dict[str, Any]] = None,
) -> str:
    review_map = {r["evaluation_id"]: r for r in (human_reviews or [])}

    green_items = [e for e in evaluations if e.get("risk_level") == "green"]
    yellow_items = [e for e in evaluations if e.get("risk_level") == "yellow"]
    red_items = [e for e in evaluations if e.get("risk_level") == "red"]

    report_lines = ["# 合同对比审查报告", ""]
    report_lines.append("## 审查摘要")
    report_lines.append(f"- 绿色（通过）: {len(green_items)} 项")
    report_lines.append(f"- 黄色（需确认）: {len(yellow_items)} 项")
    report_lines.append(f"- 红色（不可接受）: {len(red_items)} 项")
    report_lines.append("")

    if green_items:
        report_lines.append("## 绿色项（符合标准）")
        for item in green_items:
            report_lines.extend(_item_lines(item, review_map, include_risk=False))
        report_lines.append("")

    if yellow_items:
        report_lines.append("## 黄色项（需人工确认）")
        for item in yellow_items:
            report_lines.extend(_item_lines(item, review_map, include_risk=False))
        report_lines.append("")

    if red_items:
        report_lines.append("## 红色项（违反合规）")
        for item in red_items:
            report_lines.extend(_item_lines(item, review_map, include_risk=True))
        report_lines.append("")

    report_lines.append("## 最终建议")
    if red_items:
        unapproved_red = [
            item for item in red_items
            if not review_map.get(item.get("id"), {}).get("approved")
        ]
        if unapproved_red:
            report_lines.append("存在未批准的红色风险项，建议与合同对方协商修改后再签约。")
        else:
            report_lines.append("红色风险项已全部得到法务确认，但建议谨慎处理。")
    elif yellow_items:
        unapproved_yellow = [
            item for item in yellow_items
            if not review_map.get(item.get("id"), {}).get("approved")
        ]
        if unapproved_yellow:
            report_lines.append("存在尚未批准的黄色风险项，建议法务确认后再继续流程。")
        else:
            report_lines.append("黄色风险项已得到法务确认，可以继续流程。")
    else:
        report_lines.append("合同经审查未发现重大合规风险，可以继续流程。")

    return "\n".join(report_lines)


def _review_status(review: Dict[str, Any]) -> str:
    if not review:
        return "待确认"
    if review.get("approved"):
        return "已批准"
    return "已拒绝"


def _item_lines(item: Dict[str, Any], review_map: Dict[Any, Dict[str, Any]], include_risk: bool) -> List[str]:
    review = review_map.get(item.get("id"), {})
    suggestion = review.get("modified_suggestion") or item.get("suggestion") or ""
    difference = item.get("difference") or {}
    lines = [f"- [{_review_status(review)}] {item.get('explanation', '')}"]
    original = (difference.get("original_section") or "")[:100]
    modified = (difference.get("modified_section") or "")[:100]
    if original:
        lines.append(f"  原文: {original}")
    if modified:
        lines.append(f"  修改: {modified}")
    if include_risk:
        matched = item.get("matched_rule") or {}
        lines.append(f"  风险: {matched.get('description') or '高风险条款'}")
    if suggestion:
        lines.append(f"  建议: {suggestion}")
    if review.get("comment"):
        lines.append(f"  法务意见: {review['comment']}")
    templates = item.get("reference_templates") or []
    if templates:
        lines.append(f"  参考模板: {'、'.join(templates)}")
    return lines
