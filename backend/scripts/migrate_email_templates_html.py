"""邮件模板 body_html 迁移辅助函数。"""

import re
import html
from html.parser import HTMLParser

_STYLE_RE = re.compile(r"<style[\s>].*?</style>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[a-zA-Z][^>]*>|</[a-zA-Z][^>]*>|<[a-zA-Z][^>]*/\s*>")


def classify_html(body_html: str | None) -> str:
    """分类 body_html 内容。"""
    if body_html is None or body_html.strip() == "":
        return "empty_html"

    without_style = _STYLE_RE.sub("", body_html).strip()

    if _TAG_RE.search(body_html) and not without_style:
        return "style_only"

    if _TAG_RE.search(body_html):
        return "proper_html"

    return "raw_text"


def raw_text_to_html(text: str) -> str:
    """将已被 bleach 转义的裸文本转为段落 HTML（不做二次 escape）。"""
    paragraphs = text.split("\n\n")
    parts = []
    for p in paragraphs:
        inner = p.replace("\n", "<br>")
        parts.append(f"<p>{inner}</p>")
    return "".join(parts)


def plain_text_to_html(text: str) -> str:
    """将纯文本转为 HTML（先 escape 再转换）。"""
    escaped = html.escape(text)
    return raw_text_to_html(escaped)


class _TextExtractor(HTMLParser):
    """从 HTML 提取纯文本的解析器。"""

    def __init__(self):
        super().__init__()
        self._pieces: list[str] = []
        self._block_tags = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "blockquote"}

    def handle_starttag(self, tag: str, attrs):
        if tag == "br":
            self._pieces.append("\n")

    def handle_endtag(self, tag: str):
        if tag in self._block_tags:
            self._pieces.append("\n")

    def handle_data(self, data: str):
        self._pieces.append(data)

    def get_text(self) -> str:
        return "".join(self._pieces).strip()


def text_from_html(body_html: str | None) -> str:
    """从 HTML 提取纯文本。"""
    if not body_html:
        return ""
    parser = _TextExtractor()
    parser.feed(body_html)
    return parser.get_text()


# ---------------------------------------------------------------------------
# 迁移主逻辑
# ---------------------------------------------------------------------------

import argparse
import sys

import psycopg


def migrate_table(
    conn: psycopg.Connection,
    table_name: str,
    dry_run: bool,
) -> dict:
    """迁移单张表的 body_html / body_text / body_design。

    返回统计字典。
    """
    cur = conn.execute(
        f"SELECT id, body_html, body_text, body_design FROM {table_name}"
    )
    rows = cur.fetchall()

    stats = {
        "total": len(rows),
        "proper_html": 0,
        "raw_text": 0,
        "style_only": 0,
        "empty_html": 0,
        "body_text_filled": 0,
        "body_design_cleared": 0,
    }

    for row_id, body_html, body_text, body_design in rows:
        classification = classify_html(body_html)
        stats[classification] += 1

        new_body_html = body_html
        html_changed = False

        if classification == "proper_html":
            pass  # body_html 不动
        elif classification == "raw_text":
            new_body_html = raw_text_to_html(body_html)
            html_changed = True
        elif classification == "style_only":
            if body_text and body_text.strip():
                new_body_html = plain_text_to_html(body_text)
                html_changed = True
        elif classification == "empty_html":
            if body_text and body_text.strip():
                new_body_html = plain_text_to_html(body_text)
                html_changed = True

        # 如果 body_text 为空但转换后的 body_html 有内容，从 HTML 提取
        text_filled = False
        new_body_text = body_text
        if (not body_text or not body_text.strip()) and new_body_html and new_body_html.strip():
            new_body_text = text_from_html(new_body_html)
            if new_body_text:
                text_filled = True
                stats["body_text_filled"] += 1

        # body_design 一律设为 NULL
        design_changed = body_design is not None
        if design_changed:
            stats["body_design_cleared"] += 1

        # 判断是否需要更新
        needs_update = html_changed or text_filled or design_changed

        if dry_run:
            if needs_update:
                print(
                    f"  [{table_name}] id={row_id}  分类={classification}  "
                    f"html变更={html_changed}  补填text={text_filled}  "
                    f"清除design={design_changed}"
                )
        else:
            if needs_update:
                conn.execute(
                    f"UPDATE {table_name} "
                    "SET body_html = %s, body_text = %s, body_design = %s "
                    "WHERE id = %s",
                    (new_body_html, new_body_text, None, row_id),
                )

    return stats


def _print_stats(table_name: str, stats: dict) -> None:
    """打印统计信息。"""
    print(f"\n=== {table_name} 统计 ===")
    print(f"  总记录数:        {stats['total']}")
    print(f"  proper_html:     {stats['proper_html']}")
    print(f"  raw_text:        {stats['raw_text']}")
    print(f"  style_only:      {stats['style_only']}")
    print(f"  empty_html:      {stats['empty_html']}")
    print(f"  补填 body_text:  {stats['body_text_filled']}")
    print(f"  清除 body_design:{stats['body_design_cleared']}")


def main() -> None:
    """迁移入口：解析参数、连接数据库、执行迁移。"""
    parser = argparse.ArgumentParser(
        description="迁移邮件模板 body_html / body_text / body_design"
    )
    parser.add_argument(
        "--db-url",
        required=True,
        help="PostgreSQL 连接串，例如 postgresql://user:pass@host:5432/dbname",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行写库；不传该参数时只输出 dry-run 计划",
    )
    args = parser.parse_args()

    dry_run = not args.execute
    if dry_run:
        print(">>> DRY-RUN 模式（不会写库，传 --execute 以实际执行）\n")
    else:
        print(">>> 执行模式（将写入数据库）\n")

    tables = ["email_templates", "platform_email_templates"]

    with psycopg.connect(args.db_url) as conn:
        for table in tables:
            print(f"--- 处理表: {table} ---")
            stats = migrate_table(conn, table, dry_run)
            _print_stats(table, stats)

        if dry_run:
            print("\n>>> DRY-RUN 完成，未提交任何变更。")
            conn.rollback()
        else:
            conn.commit()
            print("\n>>> 迁移完成，已提交。")


if __name__ == "__main__":
    main()
