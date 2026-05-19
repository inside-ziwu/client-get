CONTACT_COUNT_RANGE_SQL = {
    "0": "{alias}.contacts_count = 0",
    "1-3": "{alias}.contacts_count BETWEEN 1 AND 3",
    "4-10": "{alias}.contacts_count BETWEEN 4 AND 10",
    "11-30": "{alias}.contacts_count BETWEEN 11 AND 30",
    "30+": "{alias}.contacts_count > 30",
}


def contact_count_range_clause(range_value: str | None, alias: str = "cc") -> str | None:
    template = CONTACT_COUNT_RANGE_SQL.get(range_value or "")
    return template.format(alias=alias) if template else None


def pcb_supplier_presence_clause(value: str | None, alias: str = "cc") -> str | None:
    if value == "has":
        return f"COALESCE(cardinality({alias}.pcb_suppliers), 0) > 0"
    if value == "none":
        return f"COALESCE(cardinality({alias}.pcb_suppliers), 0) = 0"
    return None


def employee_count_lower_expr(alias: str = "cc", column: str = "employee_num") -> str:
    field = f"{alias}.{column}"
    return f"""
CASE
  WHEN {field} IS NULL OR btrim({field}) = '' THEN NULL
  WHEN {field} ~ E'[0-9]' THEN replace(substring({field} FROM E'([0-9][0-9,]*)'), ',', '')::int
  ELSE NULL
END
"""


def employee_count_upper_expr(alias: str = "cc", column: str = "employee_num") -> str:
    field = f"{alias}.{column}"
    return f"""
CASE
  WHEN {field} IS NULL OR btrim({field}) = '' THEN NULL
  WHEN {field} ~ E'[0-9][0-9,]*\\s*[-–~至]\\s*[0-9][0-9,]*' THEN
    replace(substring({field} FROM E'[0-9][0-9,]*\\s*[-–~至]\\s*([0-9][0-9,]*)'), ',', '')::int
  WHEN {field} ~ E'(以上|\\+)' THEN NULL
  WHEN {field} ~ E'[0-9]' THEN replace(substring({field} FROM E'([0-9][0-9,]*)'), ',', '')::int
  ELSE NULL
END
"""


def append_employee_count_range(
    where_parts: list[str],
    params: dict,
    *,
    employee_count_min: int | None,
    employee_count_max: int | None,
    alias: str = "cc",
    column: str = "employee_num",
) -> None:
    if employee_count_min is None and employee_count_max is None:
        return

    lower_expr = employee_count_lower_expr(alias, column)
    upper_expr = employee_count_upper_expr(alias, column)
    where_parts.append(f"({lower_expr}) IS NOT NULL")
    if employee_count_min is not None:
        where_parts.append(f"(({upper_expr}) IS NULL OR ({upper_expr}) >= :employee_count_min)")
        params["employee_count_min"] = employee_count_min
    if employee_count_max is not None:
        where_parts.append(f"({lower_expr}) <= :employee_count_max")
        params["employee_count_max"] = employee_count_max
