import pytest

from app.integrations.engagelab import EngageLabSendError, classify_send_error


def _error(
    status_code: int | None,
    detail: str | None = None,
    *,
    provider_code: int | None = None,
    outcome: str = "rejected",
) -> EngageLabSendError:
    return EngageLabSendError(
        status_code=status_code,
        provider_code=provider_code,
        detail=detail or "",
        outcome=outcome,
    )


def test_quota_error_matches_production_engagelab_signature():
    """2026-07-02 实测 HTTP 400 + code 30877 + 余额不足原文仍归配额。"""
    detail = (
        "mail failed to send. 552 "
        "{'code':-7,'message':'your account balance is not enough,please recharge soon'}"
    )

    result = classify_send_error(_error(400, detail, provider_code=30877))

    assert result["is_permanent"] is False
    assert result["error_type"] == "quota"
    assert result["error_category"] == "quota"
    assert result["decision"] == "defer_quota"


def test_verified_balance_phrase_is_quota_but_broad_quota_words_are_not():
    """「余额不足」保留；未核实的 Daily Quota 文案不再打开配额熔断。"""
    balance = classify_send_error(_error(400, "账户余额不足，请充值"))
    broad = classify_send_error(_error(400, "Daily Quota exceeded"))

    assert balance["error_type"] == "quota"
    assert balance["error_category"] == "quota"
    assert broad["error_type"] == "temporary"
    assert broad["error_category"] is None
    assert broad["decision"] == "retry"


def test_single_rate_limit_is_temporary_not_quota():
    """单次 429 走限流重试，不直接判配额。"""
    result = classify_send_error(_error(429, "too many requests"))

    assert result["is_permanent"] is False
    assert result["error_type"] == "rate_limit"
    assert result["error_category"] is None
    assert result["decision"] == "retry"


def test_bare_422_is_not_invalid_recipient():
    """没有已核实的发送接口收件人业务码时，裸 422 不标联系人 invalid。"""
    result = classify_send_error(_error(422, "invalid recipient"))

    assert result["is_permanent"] is False
    assert result["error_type"] == "temporary"
    assert result["error_category"] is None
    assert result["error_class"] == "unknown"


def test_unknown_4xx_is_temporary():
    """未知 4xx 默认临时失败，不立即终止 enrollment。"""
    result = classify_send_error(_error(456, "unknown provider error"))

    assert result["is_permanent"] is False
    assert result["error_type"] == "temporary"
    assert result["error_category"] is None


@pytest.mark.parametrize(
    ("status_code", "detail"),
    [
        (503, None),
        (503, ""),
        (503, "server unavailable"),
    ],
)
def test_5xx_paths_remain_temporary(status_code: int, detail: str | None):
    """5xx 保持临时失败，可按既有退避重试。"""
    result = classify_send_error(_error(status_code, detail))

    assert result["is_permanent"] is False
    assert result["error_type"] == "temporary"
    assert result["error_category"] is None


def test_network_outcome_is_isolated_not_resent():
    """超时、连接失败和没有回执的未知异常记为结果未知，不自动重发。"""
    result = classify_send_error(_error(None, None, outcome="uncertain"))

    assert result["is_permanent"] is False
    assert result["error_type"] == "uncertain"
    assert result["error_category"] is None
    assert result["decision"] == "isolate"


@pytest.mark.parametrize(
    "detail",
    [
        "provider 503 rate limit",
        "provider 503 配额 exhausted",
    ],
)
def test_5xx_text_signals_do_not_trigger_rate_or_quota_classification(detail: str):
    result = classify_send_error(_error(503, detail))

    assert result["is_permanent"] is False
    assert result["error_type"] == "temporary"
    assert result["error_category"] is None
