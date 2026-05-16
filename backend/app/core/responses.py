from typing import Any


def success_response(data: Any) -> dict[str, Any]:
    return {"data": data}


def paginated_response(
    data: list[Any],
    *,
    cursor: str | None = None,
    has_more: bool = False,
    total: int = 0,
) -> dict[str, Any]:
    return {
        "data": data,
        "pagination": {
            "cursor": cursor,
            "has_more": has_more,
            "total": total,
        },
    }

