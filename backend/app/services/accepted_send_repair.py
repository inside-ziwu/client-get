"""历史接单回写失败的只读汇总。

本地 failed 且没有 provider id 只能说明回写事务没留下回执，不能据此计算
服务商实际接单次数，也不能调用 mark_email_sent。
"""

from collections import defaultdict


def summarize_candidates(rows: list[dict]) -> dict:
    """按实例、租户、enrollment、step 汇总。不输出邮箱或 message id。"""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("instance_id"),
            str(row.get("tenant_id")),
            str(row.get("enrollment_id")),
            str(row.get("step_id")),
        )
        groups[key].append(row)

    summary = {
        "group_count": len(groups),
        "single_failed_without_provider_id": 0,
        "multiple_failed_same_step": 0,
        "needs_verification": 0,
        "groups": [],
    }
    for key, items in groups.items():
        local_failed_count = len(items)
        if local_failed_count == 1:
            summary["single_failed_without_provider_id"] += 1
        else:
            summary["multiple_failed_same_step"] += 1
        summary["needs_verification"] += 1
        summary["groups"].append(
            {
                "instance_id": key[0],
                "tenant_id": key[1],
                "enrollment_id": key[2],
                "step_id": key[3],
                "local_failed_count": local_failed_count,
                "email_ids": [str(item["email_id"]) for item in items],
                "lock_status": items[0].get("lock_status"),
                "verdict": "needs_verification",
            }
        )
    return summary


def correlate_receipts(summary: dict, receipts: list[dict]) -> dict:
    """用外部只读回执清单标注是否有对应关系。不回显 message id，只回显长度。"""
    by_email = {}
    for receipt in receipts:
        email_id = str(receipt.get("email_id") or "")
        if not email_id:
            continue
        message_id = receipt.get("message_id")
        by_email[email_id] = {
            "accepted": bool(receipt.get("accepted")),
            "message_id_length": len(message_id) if isinstance(message_id, str) else None,
        }

    matched = 0
    unmatched = 0
    for group in summary["groups"]:
        hits = [by_email[email_id] for email_id in group["email_ids"] if email_id in by_email]
        group["receipt_match_count"] = len(hits)
        group["receipt_id_lengths"] = [hit["message_id_length"] for hit in hits]
        if hits and all(hit["accepted"] for hit in hits):
            group["verdict"] = "receipt_present_needs_verification"
            matched += 1
        else:
            group["verdict"] = "needs_verification"
            unmatched += 1
    summary["groups_with_receipt"] = matched
    summary["groups_without_receipt"] = unmatched
    return summary


def candidate_sql(has_lock_receipt_columns: bool) -> str:
    lock_bits = (
        """
        esl.status AS lock_status,
        (esl.provider_message_id IS NOT NULL) AS lock_has_provider_id,
        length(esl.provider_message_id) AS lock_provider_id_length
        """
        if has_lock_receipt_columns
        else """
        esl.status AS lock_status,
        false AS lock_has_provider_id,
        NULL::integer AS lock_provider_id_length
        """
    )
    return f"""
        SELECT t.instance_id,
               e.tenant_id,
               e.enrollment_id,
               e.step_id,
               e.id AS email_id,
               e.created_at,
               {lock_bits}
        FROM emails e
        JOIN tenants t ON t.id = e.tenant_id
        LEFT JOIN email_send_locks esl
          ON esl.tenant_id = e.tenant_id
         AND esl.enrollment_id = e.enrollment_id
         AND esl.step_id = e.step_id
        WHERE e.created_at >= %s
          AND e.created_at < %s
          AND e.status = 'failed'
          AND e.sent_at IS NULL
          AND e.engagelab_message_id IS NULL
          AND (%s::text IS NULL OR t.instance_id = %s)
        ORDER BY t.instance_id, e.enrollment_id, e.step_id, e.created_at, e.id
    """
