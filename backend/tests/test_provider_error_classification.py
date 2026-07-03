import pytest

from app.workers.sending import SendingWorker


@pytest.fixture
def worker() -> SendingWorker:
    return SendingWorker()


def test_quota_error_matches_production_engagelab_signature(worker: SendingWorker):
    """覆盖 AE1：2026-07-02 实测余额不足签名必须归类为配额错误。"""
    message = (
        '{"code": 30877, "message": "mail failed to send. 552 '
        "{'code':-7,'message':'your account balance is not enough,please recharge soon'}\"}"
    )

    result = worker._classify_provider_error(400, message)

    assert result == {
        "is_permanent": False,
        "error_type": "quota",
        "error_category": "quota",
    }


@pytest.mark.parametrize(
    "message",
    [
        "Daily Quota exceeded",
        "账户余额不足，请充值",
    ],
)
def test_quota_error_matches_case_insensitive_and_chinese_keywords(
    worker: SendingWorker, message: str
):
    """覆盖 AE1：大小写混合与中文兜底词也必须命中配额类。"""
    result = worker._classify_provider_error(400, message)

    assert result["is_permanent"] is False
    assert result["error_type"] == "quota"
    assert result["error_category"] == "quota"


def test_single_rate_limit_is_temporary_not_quota(worker: SendingWorker):
    """覆盖 AE2：单次 429 限流走临时重试链，不直接判配额。"""
    result = worker._classify_provider_error(429, "too many requests")

    assert result == {
        "is_permanent": False,
        "error_type": "rate_limit",
        "error_category": None,
    }


def test_422_remains_invalid_permanent(worker: SendingWorker):
    """覆盖 AE4/AE15：422 无效收件人维持永久 invalid。"""
    result = worker._classify_provider_error(422, "invalid recipient")

    assert result == {
        "is_permanent": True,
        "error_type": "permanent",
        "error_category": "invalid",
    }


def test_unknown_4xx_is_temporary(worker: SendingWorker):
    """覆盖 AE14：未知 4xx 默认临时失败，不立即终止 enrollment。"""
    result = worker._classify_provider_error(456, "unknown provider error")

    assert result == {
        "is_permanent": False,
        "error_type": "temporary",
        "error_category": None,
    }


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (None, None),
        (None, ""),
        (503, "server unavailable"),
    ],
)
def test_network_and_5xx_paths_remain_temporary(
    worker: SendingWorker, status_code: int | None, message: str | None
):
    """覆盖 R3：网络异常路径与 5xx 保持临时失败。"""
    result = worker._classify_provider_error(status_code, message)

    assert result == {
        "is_permanent": False,
        "error_type": "temporary",
        "error_category": None,
    }


@pytest.mark.parametrize(
    "message",
    [
        "provider 503 rate limit",
        "provider 503 配额 exhausted",
    ],
)
def test_5xx_text_signals_do_not_trigger_rate_or_quota_classification(
    worker: SendingWorker, message: str
):
    result = worker._classify_provider_error(503, message)

    assert result == {
        "is_permanent": False,
        "error_type": "temporary",
        "error_category": None,
    }
