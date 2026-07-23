"""数据库结构契约工具：导出结构快照 + 渲染人读文档（issue #61 ④ 的落地）。

用法（在 backend/ 目录下）::

    uv run python scripts/schema_snapshot.py          # 连开发库（CLIENTGET_DEV_DATABASE_URL）
    uv run python scripts/schema_snapshot.py --prod   # 连生产库（CLIENTGET_PROD_DATABASE_URL）

输出三个文件（均纳入 git，本脚本不执行任何 git 操作）：

- ``backend/03_database/schema_snapshot.json`` —— **机器契约**：纯结构（表/列/约束/索引/
  视图/alembic 版本），不含行数、时间戳等波动数据。``git diff`` 它即带外变更探测器：
  迁移合并后重跑，diff 应恰好等于迁移内容；出现迁移之外的变化 = 有人带外改库。
- ``docs/database-schema.md`` —— 人读文档（含行数参考，故其 diff 有噪音，不作契约用）。
- ``docs/database-schema.dbml`` —— 紧凑结构总览，可贴入 dbdiagram.io 生成 ER 图。

业务语义两个来源（人工维护，与机器结构分离）：
``backend/03_database/schema_docs.json``（域分组 + 表/列说明）、
``backend/03_database/schema_notes.md``（漂移注记章节）。

安全：连接设置 ``read_only``（所有事务以 READ ONLY 开启）并二次校验，任何写操作会被
PostgreSQL 拒绝；连接串仅在内存使用，不写入任何输出。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env.local"
SNAPSHOT_FILE = BACKEND_DIR / "03_database" / "schema_snapshot.json"
DOCS_FILE = BACKEND_DIR / "03_database" / "schema_docs.json"
NOTES_FILE = BACKEND_DIR / "03_database" / "schema_notes.md"
MD_FILE = REPO_ROOT / "docs" / "database-schema.md"
DBML_FILE = REPO_ROOT / "docs" / "database-schema.dbml"

BACKUP_TABLE_RE = re.compile(r"^backup_|_backup_\d{8}_\d{6}$")


def is_backup_table(name: str) -> bool:
    return bool(BACKUP_TABLE_RE.search(name))


def load_db_url(key: str) -> str:
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            return re.sub(r"^postgresql\+\w+://", "postgresql://", val)
    raise SystemExit(f"{key} 不存在于 {ENV_FILE}")


# ---------------------------------------------------------------- 导出

def export_structure(conn: psycopg.Connection) -> tuple[dict, dict]:
    """返回 (snapshot, volatile)。snapshot 为纯结构契约；volatile 为行数、
    分区子表名单等仅供 markdown 渲染的波动数据。"""
    cur = conn.cursor()

    cur.execute("SHOW transaction_read_only")
    if cur.fetchone()["transaction_read_only"] != "on":
        raise SystemExit("会话不是只读模式，中止")

    cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
    alembic = [r["version_num"] for r in cur.fetchall()]

    cur.execute(
        """
        SELECT c.relname AS name,
               c.relkind::text AS relkind,
               c.relispartition,
               obj_description(c.oid, 'pg_class') AS comment,
               pg_get_partkeydef(c.oid) AS partition_key,
               c.reltuples::bigint AS approx_rows,
               CASE WHEN c.relispartition THEN
                 (SELECT pc.relname FROM pg_inherits i
                  JOIN pg_class pc ON pc.oid = i.inhparent
                  WHERE i.inhrelid = c.oid LIMIT 1)
               END AS parent_table
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
        ORDER BY c.relname
        """
    )
    raw_tables = cur.fetchall()

    cur.execute(
        """
        SELECT c.relname AS table_name,
               a.attname AS name,
               format_type(a.atttypid, a.atttypmod) AS type,
               NOT a.attnotnull AS nullable,
               pg_get_expr(d.adbin, d.adrelid) AS default,
               a.attidentity::text AS identity,
               col_description(c.oid, a.attnum) AS comment
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND NOT c.relispartition AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum
        """
    )
    raw_columns = cur.fetchall()

    cur.execute(
        """
        SELECT cl.relname AS table_name,
               con.conname AS name,
               con.contype::text AS type,
               pg_get_constraintdef(con.oid) AS definition
        FROM pg_constraint con
        JOIN pg_class cl ON cl.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = cl.relnamespace
        WHERE n.nspname = 'public' AND NOT cl.relispartition
        ORDER BY cl.relname, con.contype, con.conname
        """
    )
    raw_constraints = cur.fetchall()

    cur.execute(
        """
        SELECT t.relname AS table_name,
               i.relname AS name,
               pg_get_indexdef(ix.indexrelid) AS definition
        FROM pg_index ix
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public' AND NOT t.relispartition
        ORDER BY t.relname, i.relname
        """
    )
    raw_indexes = cur.fetchall()

    cur.execute(
        """
        SELECT c.relname AS name, pg_get_viewdef(c.oid, true) AS definition
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'v'
          AND c.relname NOT LIKE 'pg\\_stat%'
        ORDER BY c.relname
        """
    )
    views = {r["name"]: r["definition"].rstrip() for r in cur.fetchall()}

    cols_by_table: dict[str, list] = defaultdict(list)
    for c in raw_columns:
        entry = {"name": c["name"], "type": c["type"], "nullable": c["nullable"]}
        if c["default"] is not None:
            entry["default"] = c["default"]
        if c["identity"]:
            entry["identity"] = c["identity"]
        if c["comment"]:
            entry["comment"] = c["comment"]
        cols_by_table[c["table_name"]].append(entry)

    cons_by_table: dict[str, list] = defaultdict(list)
    for c in raw_constraints:
        cons_by_table[c["table_name"]].append(
            {"name": c["name"], "type": c["type"], "definition": c["definition"]}
        )

    idx_by_table: dict[str, list] = defaultdict(list)
    for i in raw_indexes:
        idx_by_table[i["table_name"]].append(
            {"name": i["name"], "definition": i["definition"]}
        )

    tables: dict[str, dict] = {}
    backup_tables: list[str] = []
    approx_rows: dict[str, int] = {}
    partitions: dict[str, list[str]] = defaultdict(list)

    for t in raw_tables:
        name = t["name"]
        if t["relispartition"]:
            partitions[t["parent_table"]].append(name)
            continue
        approx_rows[name] = t["approx_rows"]
        if is_backup_table(name):
            backup_tables.append(name)
            continue
        if name == "alembic_version":
            continue
        entry: dict = {
            "kind": "partitioned" if t["relkind"] == "p" else "table",
            "columns": cols_by_table[name],
            "constraints": cons_by_table.get(name, []),
            "indexes": idx_by_table.get(name, []),
        }
        if t["partition_key"]:
            entry["partition_key"] = t["partition_key"]
        if t["comment"]:
            entry["comment"] = t["comment"]
        tables[name] = entry

    snapshot = {
        "_readme": (
            "数据库结构契约（机器生成，禁止手改）。生成工具 backend/scripts/schema_snapshot.py。"
            "git diff 本文件 = 带外变更探测器：迁移合并后重跑，diff 应恰好等于迁移内容。"
            "不含行数/分区子表名单/时间戳等波动数据。"
        ),
        "alembic_version": alembic,
        "tables": tables,
        "views": views,
        "backup_tables": sorted(backup_tables),
    }
    volatile = {"approx_rows": approx_rows, "partitions": dict(partitions)}
    return snapshot, volatile


# ---------------------------------------------------------------- 渲染共用

TYPE_MAP = [
    (r"^character varying\((\d+)\)$", r"VARCHAR(\1)"),
    (r"^character varying$", "VARCHAR"),
    (r"^character\((\d+)\)$", r"CHAR(\1)"),
    (r"^timestamp with time zone$", "TIMESTAMPTZ"),
    (r"^timestamp without time zone$", "TIMESTAMP"),
    (r"^time without time zone$", "TIME"),
    (r"^double precision$", "DOUBLE PRECISION"),
    (r"^numeric\(([\d,]+)\)$", r"NUMERIC(\1)"),
]


def fmt_type(t: str) -> str:
    for pat, rep in TYPE_MAP:
        if re.match(pat, t):
            return re.sub(pat, rep, t)
    if t.endswith("[]"):
        return fmt_type(t[:-2]) + "[]"
    return t.upper() if re.match(r"^[a-z ]+$", t) else t


def fmt_default(d: str | None, identity: str | None) -> str:
    if identity == "a":
        return "IDENTITY(ALWAYS)"
    if identity == "d":
        return "IDENTITY"
    if d is None:
        return ""
    d = re.sub(r"nextval\('([^']+)'::regclass\)", r"nextval(\1)", d)
    d = re.sub(r"::[a-z_ ]+(\[\])?", "", d)
    if len(d) > 48:
        d = d[:45] + "…"
    return f"`{d}`"


def parse_fk(defn: str):
    m = re.match(r"FOREIGN KEY \(([^)]+)\) REFERENCES ([\w.]+)\(([^)]+)\)(.*)", defn)
    if not m:
        return None
    cols = [c.strip() for c in m.group(1).split(",")]
    ref_table = m.group(2).replace("public.", "")
    ref_cols = [c.strip() for c in m.group(3).split(",")]
    return cols, ref_table, ref_cols, m.group(4).strip()


def check_enums(table: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for con in table["constraints"]:
        if con["type"] != "c":
            continue
        m = re.search(r"CHECK \(\(?\(?(\w+)(?:\)::text)? = ANY \(+ARRAY\[(.+?)\]", con["definition"])
        if m:
            vals = re.sub(r"::[\w ]+", "", m.group(2)).replace("'", "")
            vals = ", ".join(v.strip() for v in vals.split(","))
            if len(vals) > 70:
                vals = vals[:67] + "…"
            out[m.group(1)] = f"取值: {vals}"
    return out


def pk_columns(table: dict) -> set[str]:
    for con in table["constraints"]:
        if con["type"] == "p":
            m = re.search(r"\(([^)]+)\)", con["definition"])
            if m:
                return {c.strip() for c in m.group(1).split(",")}
    return set()


def esc(s: str) -> str:
    return s.replace("|", "\\|")


# ---------------------------------------------------------------- Markdown

def render_markdown(snapshot: dict, volatile: dict, docs: dict, notes: str, source: str) -> tuple[str, list[str]]:
    tables: dict[str, dict] = snapshot["tables"]
    col_docs: dict[str, dict[str, str]] = docs.get("tables", {})
    common_docs: dict[str, str] = docs.get("common_columns", {})
    domains = [(d["name"], d.get("description", ""), d["tables"]) for d in docs.get("domains", [])]

    grouped = {n for _, _, names in domains for n in names}
    ungrouped = sorted(n for n in tables if n not in grouped)
    warnings: list[str] = []
    if ungrouped:
        warnings.append(f"未分域表 {len(ungrouped)} 张（落入「其他」，请在 schema_docs.json 归域）: {', '.join(ungrouped)}")
        domains = domains + [("其他（未分域）", "⚠️ 新出现、尚未在 schema_docs.json 归域的表。", ungrouped)]

    n_no_doc = sum(
        1 for tname, t in tables.items() for c in t["columns"]
        if c["name"] not in pk_columns(t)
        and not (col_docs.get(tname, {}).get(c["name"]) or common_docs.get(c["name"]))
    )
    if n_no_doc:
        warnings.append(f"无业务说明的列 {n_no_doc} 个（说明维护在 schema_docs.json）")

    L: list[str] = []
    add = L.append
    approx = volatile["approx_rows"]
    partitions = volatile["partitions"]
    n_parts = sum(len(v) for v in partitions.values())
    n_parents = sum(1 for t in tables.values() if t["kind"] == "partitioned")

    add("# ClientGet 生产数据库结构文档")
    add("")
    add(f"> **来源与快照性质**：本文档由 `backend/scripts/schema_snapshot.py` 自 **{source}**"
        f"（`pg_catalog` 只读查询）自动生成，生成日期 **{date.today().isoformat()}**，"
        f"库内 alembic 版本 **{', '.join(snapshot['alembic_version'])}**。"
        "**请勿手改本文件**——结构以 `backend/03_database/schema_snapshot.json`（机器契约，diff 即带外变更探测器）为准，"
        "业务说明维护在 `schema_docs.json`，漂移注记维护在 `schema_notes.md`，改完重跑脚本渲染。")
    add(">")
    add("> **行数**为 `pg_class.reltuples` 估算值（`-1`/`0` 表示从未 ANALYZE 或确实为空），仅供判断表的活跃度。")
    add(">")
    add("> **业务说明的来源与边界**：生产库列注释覆盖率为零，「说明」列中的业务语义提炼自代码事实"
        "（services/api 层的实际读写用法、alembic 迁移注释、schema.sql 蓝图注释、DESIGN/README/docs/solutions），"
        "初版调查日期 2026-07-22。**留空 = 代码中无可靠依据**（多见于外部直写表的数据商原始字段），宁缺毋滥、不做编造；"
        "外部表（`waimaotong_*` 等）列名字面含义明确者按字面标注。若说明与代码现状冲突，以代码为准并修订 `schema_docs.json`。")
    add("")
    add(f"**总量**：业务表 **{len(tables)}** 张（其中分区父表 {n_parents} 张，当前共 {n_parts} 个分区子表）"
        f"+ 备份快照表 **{len(snapshot['backup_tables'])}** 张 + `alembic_version`；"
        f"业务视图 {len(snapshot['views'])} 个（监控扩展视图未列出）。")
    add("")

    add("## 目录")
    add("")
    for name, _, tbls in domains:
        add(f"- **{name}**：" + "、".join(f"[`{t}`](#{t})" for t in tbls))
    add("- [业务视图](#业务视图)")
    add("- [外键关系总览](#外键关系总览)")
    add("- [备份快照表](#备份快照表)")
    add("- [已知漂移与命名注记](#已知漂移与命名注记)")
    add("")

    fk_arrows: list[str] = []
    fk_edges: set[tuple[str, str]] = set()

    for dom_name, dom_desc, tbls in domains:
        add(f"## {dom_name}")
        add("")
        if dom_desc:
            add(dom_desc)
            add("")
        for tname in tbls:
            t = tables.get(tname)
            add(f"### {tname}")
            add("")
            if t is None:
                add("> ⚠️ schema_docs.json 分域中声明，但当前库不存在（请更新分域或核查带外删除）。")
                add("")
                warnings.append(f"分域声明但库中不存在的表: {tname}")
                continue

            tbl_doc = col_docs.get(tname, {}).get("__table__", "")
            if tbl_doc:
                add(tbl_doc)
                add("")
            meta_bits = []
            if t["kind"] == "partitioned":
                subs = ", ".join(f"`{p}`" for p in sorted(partitions.get(tname, [])))
                meta_bits.append(f"**分区表** `{t['partition_key']}`，子表：{subs}")
            rows = approx.get(tname, -1)
            meta_bits.append(f"估算行数 {rows:,}" if rows >= 0 else "估算行数 —（分区父表见子表）")
            if t.get("comment"):
                meta_bits.append(t["comment"])
            add("；".join(meta_bits) + "。")
            add("")

            enums = check_enums(t)
            pks = pk_columns(t)
            fk_by_col: dict[str, str] = {}
            for con in t["constraints"]:
                if con["type"] == "f":
                    parsed = parse_fk(con["definition"])
                    if parsed:
                        cols, rt, rcols, _ = parsed
                        for c, rc in zip(cols, rcols):
                            fk_by_col[c] = f"{rt}.{rc}"

            add("| 字段名 | 数据类型 | 可空 | 默认值 | 说明 |")
            add("|---|---|---|---|---|")
            for c in t["columns"]:
                notes_bits = []
                biz = col_docs.get(tname, {}).get(c["name"]) or common_docs.get(c["name"], "")
                if biz:
                    notes_bits.append(esc(biz))
                if c["name"] in pks:
                    notes_bits.append("**PK**")
                if c["name"] in fk_by_col:
                    notes_bits.append(f"FK → `{fk_by_col[c['name']]}`")
                if t["kind"] == "partitioned" and re.search(rf"\b{re.escape(c['name'])}\b", t.get("partition_key", "")):
                    notes_bits.append("分区键")
                if c["name"] in enums:
                    notes_bits.append(enums[c["name"]])
                if c.get("comment"):
                    notes_bits.append(esc(c["comment"]))
                add(
                    f"| {c['name']} | {fmt_type(c['type'])} | "
                    f"{'✓' if c['nullable'] else '✗'} | "
                    f"{esc(fmt_default(c.get('default'), c.get('identity')))} | {'；'.join(notes_bits)} |"
                )
            add("")

            uniq = [c for c in t["constraints"] if c["type"] == "u"]
            fks = [c for c in t["constraints"] if c["type"] == "f"]
            if uniq:
                add("**唯一约束**：" + "；".join(
                    f"`{re.search(r'[(](.+)[)]', u['definition']).group(1)}`" for u in uniq))
                add("")
            fk_strs = []
            for con in fks:
                parsed = parse_fk(con["definition"])
                if not parsed:
                    continue
                cols, rt, rcols, actions = parsed
                for c, rc in zip(cols, rcols):
                    arrow = f"`{rt}.{rc}` → `{tname}.{c}`"
                    if actions:
                        arrow += f"（{actions}）"
                    fk_arrows.append(arrow)
                    fk_edges.add((rt, tname))
                s = f"`{', '.join(cols)}` → `{rt}({', '.join(rcols)})`"
                if actions:
                    s += f" {actions}"
                fk_strs.append(s)
            if fk_strs:
                add("**外键**：" + "；".join(fk_strs))
                add("")
            con_names = {c["name"] for c in t["constraints"]}
            plain_idx = [i for i in t["indexes"] if i["name"] not in con_names]
            if plain_idx:
                idx_strs = []
                for i in plain_idx:
                    is_unique = i["definition"].startswith("CREATE UNIQUE")
                    m = re.search(r"USING (\w+) (\(.+?\))(?:\s+WHERE\s+(.+))?$", i["definition"])
                    if m:
                        method, cols_s, where = m.group(1), m.group(2), m.group(3)
                        s = f"`{i['name']}`{' UNIQUE' if is_unique else ''} {cols_s}"
                        if method != "btree":
                            s += f" [{method}]"
                        if where:
                            s += f" WHERE {where}" if len(where) < 60 else " [部分索引]"
                        idx_strs.append(s)
                    else:
                        idx_strs.append(f"`{i['name']}`")
                add("**索引**：" + "；".join(idx_strs))
                add("")

    add("## 业务视图")
    add("")
    for vname, vdef in snapshot["views"].items():
        add(f"### {vname}")
        add("")
        add("```sql")
        add(vdef)
        add("```")
        add("")

    add("## 外键关系总览")
    add("")
    add("方向约定：`被引用表.列 → 引用表.外键列`（即「一 → 多」）。")
    add("")
    for a in sorted(set(fk_arrows)):
        add(f"- {a}")
    add("")
    out_degree: dict[str, int] = defaultdict(int)
    for src, _ in fk_edges:
        out_degree[src] += 1
    hubs = {n for n, d in out_degree.items() if d >= 9}
    if hubs:
        add("下图为除高扇出「枢纽表」外的外键拓扑（`A --> B` 表示 B 持有指向 A 的外键）。"
            "以下枢纽表被过多表引用，为保持图形可读未画入：")
        add("")
        for h in sorted(hubs):
            refs = sorted(dst for src, dst in fk_edges if src == h)
            add(f"- **`{h}`** ← 被 {out_degree[h]} 张表引用：{'、'.join(f'`{r}`' for r in refs)}")
        add("")
    add("```mermaid")
    add("graph LR")
    for src, dst in sorted(fk_edges):
        if src not in hubs:
            add(f"    {src} --> {dst}")
    add("```")
    add("")

    add("## 备份快照表")
    add("")
    add(f"当前库现存 **{len(snapshot['backup_tables'])}** 张备份快照表（一次性运维操作留档，清理计划见 issue #61）：")
    add("")
    add("| 表名 | 估算行数 |")
    add("|---|---|")
    for n in snapshot["backup_tables"]:
        add(f"| {n} | {approx.get(n, -1):,} |")
    add("")

    add(notes.strip())
    add("")
    return "\n".join(L), warnings


# ---------------------------------------------------------------- DBML

def render_dbml(snapshot: dict, docs: dict) -> str:
    col_docs: dict[str, dict[str, str]] = docs.get("tables", {})
    L: list[str] = [
        "// ClientGet 数据库结构总览（机器生成，请勿手改；工具 backend/scripts/schema_snapshot.py）",
        "// 可整体粘贴到 https://dbdiagram.io 生成 ER 图。分区表在此视为普通表。",
        "",
        "Project clientget {",
        "  database_type: 'PostgreSQL'",
        "}",
        "",
    ]
    refs: list[str] = []
    for tname, t in snapshot["tables"].items():
        pks = pk_columns(t)
        uniq_single: set[str] = set()
        for con in t["constraints"]:
            if con["type"] == "u":
                m = re.search(r"\(([^)]+)\)", con["definition"])
                if m and "," not in m.group(1):
                    uniq_single.add(m.group(1).strip())
        L.append(f"Table {tname} {{")
        for c in t["columns"]:
            typ = fmt_type(c["type"]).replace(" ", "_")
            attrs = []
            if c["name"] in pks and len(pks) == 1:
                attrs.append("pk")
            if not c["nullable"]:
                attrs.append("not null")
            if c["name"] in uniq_single:
                attrs.append("unique")
            attr_s = f" [{', '.join(attrs)}]" if attrs else ""
            L.append(f'  "{c["name"]}" {typ}{attr_s}')
        if len(pks) > 1:
            ordered_pks = [c["name"] for c in t["columns"] if c["name"] in pks]
            L.append("  indexes {")
            L.append(f"    ({', '.join(ordered_pks)}) [pk]")
            L.append("  }")
        tbl_doc = col_docs.get(tname, {}).get("__table__", "")
        if tbl_doc:
            note = tbl_doc.replace("'", "’")
            L.append(f"  Note: '{note}'")
        L.append("}")
        L.append("")
        for con in t["constraints"]:
            if con["type"] != "f":
                continue
            parsed = parse_fk(con["definition"])
            if not parsed:
                continue
            cols, rt, rcols, actions = parsed
            if rt not in snapshot["tables"]:
                continue
            setting = " [delete: cascade]" if "ON DELETE CASCADE" in actions else ""
            if len(cols) == 1:
                refs.append(f"Ref: {tname}.\"{cols[0]}\" > {rt}.\"{rcols[0]}\"{setting}")
    L.extend(refs)
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--prod", action="store_true",
                        help="连接生产库（CLIENTGET_PROD_DATABASE_URL）；默认连开发库")
    args = parser.parse_args()

    env_key = "CLIENTGET_PROD_DATABASE_URL" if args.prod else "CLIENTGET_DEV_DATABASE_URL"
    source = "生产库（Sealos PG）" if args.prod else "开发库（Neon PG）"
    url = load_db_url(env_key)

    # 不用 startup options 传只读参数（Neon pooler 不支持），改用连接属性：
    # 之后所有事务一律以 READ ONLY 开启，写操作会被 PostgreSQL 拒绝。
    conn = psycopg.connect(url, connect_timeout=15, row_factory=dict_row)
    conn.read_only = True
    try:
        with conn:
            snapshot, volatile = export_structure(conn)
    finally:
        conn.close()

    docs = json.loads(DOCS_FILE.read_text()) if DOCS_FILE.exists() else {}
    notes = NOTES_FILE.read_text() if NOTES_FILE.exists() else ""
    # 注记源文件的头部 HTML 注释不进渲染产物
    notes = re.sub(r"^<!--.*?-->\s*", "", notes, flags=re.S)

    md, warnings = render_markdown(snapshot, volatile, docs, notes, source)
    dbml = render_dbml(snapshot, docs)

    SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n")
    MD_FILE.write_text(md)
    DBML_FILE.write_text(dbml)

    print(f"数据来源: {source}  alembic={snapshot['alembic_version']}")
    print(f"已写出: {SNAPSHOT_FILE.relative_to(REPO_ROOT)}"
          f"  ({len(snapshot['tables'])} 业务表, {len(snapshot['backup_tables'])} 备份表, {len(snapshot['views'])} 视图)")
    print(f"已写出: {MD_FILE.relative_to(REPO_ROOT)}")
    print(f"已写出: {DBML_FILE.relative_to(REPO_ROOT)}")
    for w in warnings:
        print(f"⚠️  {w}")
    print("下一步: git diff backend/03_database/schema_snapshot.json —— diff 应恰好等于预期内的迁移变化。")


if __name__ == "__main__":
    main()
