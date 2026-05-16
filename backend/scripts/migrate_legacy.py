import argparse
import json
from pathlib import Path


EXPECTED_INPUTS = {
    "company_data": "shared_companies + company_sources + tenant_companies",
    "contact_data": "shared_contacts + tenant_contacts",
    "company_analysis": "company_scores + tenant_companies",
    "keyword_list": "collection_keywords",
    "email_plans": "sending_plans + sequence_steps + sequence_enrollments + emails",
    "system_config": "platform config / encrypted credentials / env",
}


def discover_inputs(input_dir: Path | None) -> list[dict]:
    if input_dir is None or not input_dir.exists():
        return []
    discovered = []
    for item in sorted(input_dir.iterdir()):
        if item.is_file():
            discovered.append({"name": item.stem, "path": str(item), "size": item.stat().st_size})
    return discovered


def build_report(*, input_dir: Path | None, report_path: Path | None, dry_run: bool) -> dict:
    discovered = discover_inputs(input_dir)
    mappings = [
        {"source": source, "target": target, "status": "planned"}
        for source, target in EXPECTED_INPUTS.items()
    ]
    report = {
        "mode": "dry-run" if dry_run else "plan-only",
        "input_dir": str(input_dir) if input_dir else None,
        "discovered_inputs": discovered,
        "mapping_rules": mappings,
        "validation": {
            "row_count_checks": True,
            "dedupe_report": True,
            "unmatched_records_report": True,
            "recoverable_plan_report": True,
        },
        "notes": [
            "该脚本当前仅输出迁移骨架与报告模板，不连接旧库执行真实导入。",
            "真实导入需要补充旧库连接方式、样本结构或导出文件格式。",
        ],
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ClientGet legacy migration skeleton")
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--report-path", type=Path, default=Path("docs/legacy_migration_report.json"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report = build_report(input_dir=args.input_dir, report_path=args.report_path, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
