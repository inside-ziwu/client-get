"""本机可销毁 PostgreSQL 上的 Alembic 升级与双连接恢复验证。

默认跳过。设置 CLIENTGET_PRELAUNCH_LOCAL_PG=1 后，测试自行 initdb、只监听
127.0.0.1，建 prelaunch_* 库，跑真实 alembic，结束时删库并停掉该实例。
不读取、不连接开发库或生产库。
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.tenant_messaging_service import TenantMessagingService
from app.workers.sending import SendingWorker

BACKEND = Path(__file__).parents[1]
REPO = BACKEND.parent
EVIDENCE = (
    REPO
    / ".trellis"
    / "tasks"
    / "10-27-sending-rejection-isolation"
    / "research"
    / "prelaunch-verification.json"
)
PG_TOOL = "aqua:theseus-rs/postgresql-binaries@16.15.1"
PORT = 55432
PARENT_REVISION = "20260824_0002"
REVISION = "20261028_0001"
NOW = datetime(2026, 10, 27, 2, 0, tzinfo=UTC)
ACCEPTED_AT = datetime(2026, 10, 26, 15, 30, tzinfo=UTC)
USAGE_DATE = datetime(2026, 10, 23, tzinfo=UTC).date()
EMAIL_CREATED = datetime(2026, 10, 26, 1, 0, tzinfo=UTC)
SYNTHETIC_ID = "rehearsal-20261028-" + ("m" * 76) + "@example.com"
SHORT_ID = "short-receipt-20261028"
DB_NAME_RE = re.compile(r"^prelaunch_[0-9a-f]{12}$")

PARENT_DDL = (
    """
    CREATE TABLE tenants (
      id uuid PRIMARY KEY,
      instance_id varchar(50) NOT NULL
    )
    """,
    """
    CREATE TABLE sending_plans (
      id uuid PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      domain_id uuid,
      status varchar(20) NOT NULL DEFAULT 'running',
      sent_count integer NOT NULL DEFAULT 0,
      updated_at timestamptz NOT NULL DEFAULT now(),
      completed_at timestamptz
    )
    """,
    """
    CREATE TABLE sequence_steps (
      id uuid PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      plan_id uuid NOT NULL REFERENCES sending_plans(id),
      step_number integer NOT NULL,
      delay_days integer NOT NULL
    )
    """,
    """
    CREATE TABLE tenant_contacts (
      id bigint PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      contact_status text NOT NULL DEFAULT 'available',
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE sending_plan_recipients (
      id uuid PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      plan_id uuid NOT NULL REFERENCES sending_plans(id),
      tenant_contact_id bigint NOT NULL
    )
    """,
    """
    CREATE TABLE sequence_enrollments (
      id uuid PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      plan_id uuid NOT NULL REFERENCES sending_plans(id),
      plan_recipient_id uuid NOT NULL REFERENCES sending_plan_recipients(id),
      tenant_contact_id bigint NOT NULL,
      current_step integer NOT NULL DEFAULT 1,
      status varchar(20) NOT NULL DEFAULT 'active',
      send_attempt_count integer NOT NULL DEFAULT 0,
      last_step_sent_at timestamptz,
      next_step_due_at timestamptz,
      completed_at timestamptz,
      updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE domain_daily_usage (
      id uuid PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      domain_id uuid NOT NULL,
      usage_date date NOT NULL,
      daily_limit integer NOT NULL DEFAULT 100,
      reserved_count integer NOT NULL DEFAULT 0,
      updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (domain_id, usage_date)
    )
    """,
    """
    CREATE TABLE emails (
      id uuid NOT NULL,
      created_at timestamptz NOT NULL,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      plan_id uuid,
      step_id uuid,
      step_number integer,
      enrollment_id uuid,
      tenant_contact_id bigint NOT NULL,
      engagelab_message_id varchar(100),
      status varchar(20) NOT NULL DEFAULT 'queued',
      sent_at timestamptz,
      from_email varchar(255) NOT NULL DEFAULT 'sender@example.com',
      to_email varchar(255) NOT NULL DEFAULT 'buyer@example.com',
      subject text NOT NULL DEFAULT 'synthetic',
      body_html text NOT NULL DEFAULT '<p>synthetic</p>',
      PRIMARY KEY (id, created_at)
    ) PARTITION BY RANGE (created_at)
    """,
    """
    CREATE TABLE emails_p_2026_08 PARTITION OF emails
      FOR VALUES FROM ('2026-08-01+00') TO ('2026-09-01+00')
    """,
    """
    CREATE TABLE emails_p_2026_10 PARTITION OF emails
      FOR VALUES FROM ('2026-10-01+00') TO ('2026-11-01+00')
    """,
    """
    CREATE TABLE email_send_locks (
      id uuid PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      enrollment_id uuid NOT NULL REFERENCES sequence_enrollments(id),
      step_id uuid NOT NULL REFERENCES sequence_steps(id),
      status varchar(20) NOT NULL DEFAULT 'locked',
      locked_at timestamptz NOT NULL DEFAULT now(),
      released_at timestamptz,
      email_id uuid,
      CONSTRAINT email_send_locks_status_check
        CHECK (status IN ('locked', 'sent', 'failed', 'released')),
      UNIQUE (enrollment_id, step_id)
    )
    """,
)


def _new_id() -> str:
    return str(uuid4())


def _local_target(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    name = parsed.path.strip("/")
    if host not in {"127.0.0.1", "localhost"} or parsed.port != PORT:
        pytest.fail("拒绝连接：Alembic 目标不是本次本机隔离端口")
    if not DB_NAME_RE.fullmatch(name):
        pytest.fail("拒绝连接：数据库名不是本次创建的 prelaunch 库")


def _pg_bin(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["mise", "x", PG_TOOL, "--", *args],
        check=check,
        text=True,
        capture_output=True,
    )


def _alembic_env(sync_url: str) -> dict[str, str]:
    _local_target(sync_url)
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": os.environ.get("LANG", "C"),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "APP_ENV": "local",
        "CLIENTGET_INSTANCE_ID": "default",
        "JWT_SECRET": "test-secret-key-for-unit-tests",
        "CLIENTGET_JWT_SECRET": "test-secret-key-for-unit-tests",
        "ADMIN_EMAIL": "test@example.com",
        "ADMIN_PASSWORD": "test-password",
        "DATA_SOURCE_ENCRYPTION_KEY": "test-encryption-key-0123456789abcdef",
        "INTERNAL_SERVICE_SECRET": "test-internal-secret",
        "ENGAGELAB_WEBHOOK_SECRET": "test-webhook-secret",
        "CLIENTGET_DEV_DATABASE_URL": "",
        "CLIENTGET_PROD_DATABASE_URL": "",
        "DATABASE_URL": sync_url,
        "SYNC_DATABASE_URL": sync_url,
    }


def _run_alembic(sync_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = _alembic_env(sync_url)
    check = subprocess.run(
        [sys.executable, "-c", _SETTINGS_CHECK],
        cwd=BACKEND,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check.returncode != 0:
        pytest.fail(f"Alembic 目标校验失败：{check.stdout} {check.stderr}")
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


_SETTINGS_CHECK = """
from urllib.parse import urlparse
from app.core.config import get_settings
url = get_settings().sync_database_url
parsed = urlparse(url.replace("postgresql+psycopg", "postgresql", 1))
host = (parsed.hostname or "").lower()
name = parsed.path.strip("/")
if host not in {"127.0.0.1", "localhost"} or parsed.port != 55432:
    raise SystemExit("refusing non-local alembic target")
if not name.startswith("prelaunch_"):
    raise SystemExit("refusing unexpected database name")
print(f"host={host} port={parsed.port} db={name}")
"""


def _revision(conn) -> str | None:
    exists = conn.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'alembic_version'
        """
    ).fetchone()
    if exists is None:
        return None
    row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    return None if row is None else row[0]


def _message_types(conn) -> dict[str, list]:
    rows = conn.execute(
        """
        SELECT table_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name = 'engagelab_message_id'
          AND table_name LIKE 'emails%'
        ORDER BY table_name
        """
    ).fetchall()
    return {name: [data_type, length] for name, data_type, length in rows}


def _lock_indexes(conn) -> list[str]:
    rows = conn.execute(
        """
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'email_send_locks'
        ORDER BY indexname
        """
    ).fetchall()
    return [row[0] for row in rows]


def _constraint(conn) -> str:
    row = conn.execute(
        """
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'email_send_locks_status_check'
        """
    ).fetchone()
    return "" if row is None else row[0]


def _write_evidence(payload: dict) -> None:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")


@pytest.fixture(scope="module")
def prelaunch_db():
    if os.getenv("CLIENTGET_PRELAUNCH_LOCAL_PG") != "1":
        pytest.skip("未设置 CLIENTGET_PRELAUNCH_LOCAL_PG=1，跳过本机隔离库验证")
    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", PORT))
    except OSError as exc:
        pytest.fail(f"端口 {PORT} 已被占用，拒绝附着未知数据库：{exc}")
    finally:
        probe.close()

    data = Path(f"/tmp/clientget-prelaunch-20261028-{os.getpid()}")
    db_name = f"prelaunch_{uuid4().hex[:12]}"
    assert DB_NAME_RE.fullmatch(db_name)
    started = False
    created = False
    info = {
        "data_dir": str(data),
        "db_name": db_name,
        "port": PORT,
        "cleanup": {},
    }
    try:
        if data.exists():
            pytest.fail("隔离数据目录已存在，拒绝复用")
        init = _pg_bin(
            "initdb",
            "-D",
            str(data),
            "--username",
            "postgres",
            "--auth",
            "trust",
            "--encoding",
            "UTF8",
            "--locale=C",
            check=False,
        )
        if init.returncode != 0:
            if data.is_dir() and data.name.startswith("clientget-prelaunch-20261028-"):
                shutil.rmtree(data)
            pytest.fail(f"initdb 失败：{init.stderr[-500:]}")
        (data / "PRELAUNCH_OWNER").write_text(f"{os.getpid()}\n")
        start = _pg_bin(
            "pg_ctl",
            "-D",
            str(data),
            "-l",
            str(data / "server.log"),
            "-o",
            f"-p {PORT} -k {data} -c listen_addresses=127.0.0.1",
            "-w",
            "start",
            check=False,
        )
        if start.returncode != 0:
            pytest.fail(f"pg_ctl start 失败：{start.stderr[-500:]}")
        started = True
        admin_url = f"postgresql://postgres@127.0.0.1:{PORT}/postgres"
        with psycopg.connect(admin_url, autocommit=True) as admin:
            version = admin.execute("SELECT version()").fetchone()[0]
            listen = admin.execute("SHOW listen_addresses").fetchone()[0]
            if listen != "127.0.0.1":
                pytest.fail(f"隔离库监听地址不是 127.0.0.1：{listen}")
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            created = True
        info["postgres_version"] = version
        sync_url = f"postgresql+psycopg://postgres@127.0.0.1:{PORT}/{db_name}"
        async_url = f"postgresql+asyncpg://postgres@127.0.0.1:{PORT}/{db_name}"
        plain_url = f"postgresql://postgres@127.0.0.1:{PORT}/{db_name}"
        _local_target(sync_url)
        info.update(sync_url=sync_url, async_url=async_url, plain_url=plain_url)
        yield info
    finally:
        cleanup = info["cleanup"]
        if created:
            admin_url = f"postgresql://postgres@127.0.0.1:{PORT}/postgres"
            try:
                with psycopg.connect(admin_url, autocommit=True) as admin:
                    current = admin.execute("SELECT current_database()").fetchone()[0]
                    if current != "postgres":
                        cleanup["drop_database"] = "refused_unexpected_maintenance_db"
                    else:
                        admin.execute(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                            "WHERE datname = %s AND pid <> pg_backend_pid()",
                            (db_name,),
                        )
                        admin.execute(
                            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name))
                        )
                        left = admin.execute(
                            "SELECT count(*) FROM pg_database WHERE datname = %s",
                            (db_name,),
                        ).fetchone()[0]
                        cleanup["drop_database"] = "gone" if left == 0 else "still_present"
            except Exception as exc:
                cleanup["drop_database"] = f"failed:{type(exc).__name__}"
        if started:
            stop = _pg_bin("pg_ctl", "-D", str(data), "-m", "fast", "-w", "stop", check=False)
            cleanup["pg_ctl_stop"] = stop.returncode
        marker = data / "PRELAUNCH_OWNER"
        if (
            data.is_dir()
            and marker.is_file()
            and marker.read_text().strip() == str(os.getpid())
            and data.name.startswith("clientget-prelaunch-20261028-")
        ):
            shutil.rmtree(data)
            cleanup["data_dir"] = "removed" if not data.exists() else "still_present"
        if EVIDENCE.exists():
            payload = json.loads(EVIDENCE.read_text())
            payload["cleanup"] = cleanup
            _write_evidence(payload)


def _install_parent(conn) -> None:
    for statement in PARENT_DDL:
        conn.execute(statement)


def _seed_plan(
    conn,
    instance_id: str,
    *,
    with_next_step: bool = True,
    contact_seq: int | None = None,
) -> dict:
    tenant_id = _new_id()
    plan_id = _new_id()
    domain_id = _new_id()
    step_one = _new_id()
    step_two = _new_id() if with_next_step else None
    if contact_seq is None:
        contact_seq = 1000 if instance_id == "default" else 5000
    conn.execute(
        "INSERT INTO tenants (id, instance_id) VALUES (%s, %s)",
        (tenant_id, instance_id),
    )
    conn.execute(
        """
        INSERT INTO sending_plans (id, tenant_id, domain_id, status, sent_count)
        VALUES (%s, %s, %s, 'running', 0)
        """,
        (plan_id, tenant_id, domain_id),
    )
    if with_next_step:
        conn.execute(
            """
            INSERT INTO sequence_steps (id, tenant_id, plan_id, step_number, delay_days)
            VALUES (%s, %s, %s, 1, 0), (%s, %s, %s, 2, 3)
            """,
            (step_one, tenant_id, plan_id, step_two, tenant_id, plan_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO sequence_steps (id, tenant_id, plan_id, step_number, delay_days)
            VALUES (%s, %s, %s, 1, 0)
            """,
            (step_one, tenant_id, plan_id),
        )
    conn.execute(
        """
        INSERT INTO domain_daily_usage
          (id, tenant_id, domain_id, usage_date, daily_limit, reserved_count)
        VALUES (%s, %s, %s, %s, 100, 4)
        """,
        (_new_id(), tenant_id, domain_id, USAGE_DATE),
    )
    return {
        "tenant_id": tenant_id,
        "plan_id": plan_id,
        "domain_id": domain_id,
        "step_one": step_one,
        "step_two": step_two,
        "contact_seq": contact_seq,
    }


def _add_enrollment(conn, plan: dict, **fields) -> dict:
    plan["contact_seq"] += 1
    contact_id = plan["contact_seq"]
    recipient_id = _new_id()
    enrollment_id = _new_id()
    email_id = _new_id() if fields.get("with_email") else None
    lock_id = _new_id()
    conn.execute(
        "INSERT INTO tenant_contacts (id, tenant_id) VALUES (%s, %s)",
        (contact_id, plan["tenant_id"]),
    )
    conn.execute(
        """
        INSERT INTO sending_plan_recipients
          (id, tenant_id, plan_id, tenant_contact_id)
        VALUES (%s, %s, %s, %s)
        """,
        (recipient_id, plan["tenant_id"], plan["plan_id"], contact_id),
    )
    conn.execute(
        """
        INSERT INTO sequence_enrollments
          (id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (enrollment_id, plan["tenant_id"], plan["plan_id"], recipient_id, contact_id),
    )
    if email_id is not None:
        conn.execute(
            """
            INSERT INTO emails (
              id, created_at, tenant_id, plan_id, step_id, step_number, enrollment_id,
              tenant_contact_id, engagelab_message_id, status
            ) VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, 'queued')
            """,
            (
                email_id,
                EMAIL_CREATED,
                plan["tenant_id"],
                plan["plan_id"],
                plan["step_one"],
                enrollment_id,
                contact_id,
                fields.get("message_id"),
            ),
        )
    conn.execute(
        """
        INSERT INTO email_send_locks (
          id, tenant_id, enrollment_id, step_id, status, locked_at, email_id,
          provider_message_id, provider_accepted_at, dispatch_started_at, quota_usage_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            lock_id,
            plan["tenant_id"],
            enrollment_id,
            plan["step_one"],
            fields["status"],
            fields.get("locked_at", NOW),
            email_id,
            fields.get("message_id"),
            fields.get("accepted_at"),
            fields.get("started_at"),
            fields.get("quota_date"),
        ),
    )
    return {
        "email_id": email_id,
        "enrollment_id": enrollment_id,
        "lock_id": lock_id,
        "tenant_id": plan["tenant_id"],
        "plan_id": plan["plan_id"],
        "step_id": plan["step_one"],
        "message_id": fields.get("message_id"),
    }


def _engine(url: str):
    return create_async_engine(url, pool_size=1, max_overflow=0)


class _NoSend:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def send_email(self, payload: dict) -> dict:
        self.calls.append("send_email")
        raise AssertionError("恢复路径调用了 send_email")


async def _claim_first(engine, service, locked: asyncio.Event, release: asyncio.Event):
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            rows = await service.list_accepted_pending(
                conn,
                limit=20,
                as_of=NOW,
                lease_until=NOW + timedelta(seconds=15),
            )
            locked.set()
            await release.wait()
            return rows
        finally:
            await transaction.commit()


async def _claim_second(engine, service, locked: asyncio.Event, release: asyncio.Event):
    await locked.wait()
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            return await service.list_accepted_pending(
                conn,
                limit=20,
                as_of=NOW,
                lease_until=NOW + timedelta(seconds=15),
            )
        finally:
            release.set()
            await transaction.commit()


@pytest.mark.asyncio
async def test_local_alembic_upgrade_downgrade_and_concurrent_recovery(prelaunch_db):
    sync_url = prelaunch_db["sync_url"]
    plain_url = prelaunch_db["plain_url"]
    async_url = prelaunch_db["async_url"]
    evidence: dict = {
        "result": "failed",
        "host": "127.0.0.1",
        "port": PORT,
        "database": prelaunch_db["db_name"],
        "data_dir_name": Path(prelaunch_db["data_dir"]).name,
        "postgres_version": prelaunch_db["postgres_version"],
            "python": sys.version.split()[0],
            "before_fix": {
                "database": "prelaunch_f36204c45b83",
                "server_addr": "127.0.0.1/32",
                "error": "AmbiguousParameterError",
                "lock_status": "accepted_pending",
                "sent_count": 0,
                "same_service_sql": True,
            },
        "commands": [
            f"mise x {PG_TOOL} -- initdb -D <fresh-tmpdir> --auth trust --locale=C",
            f"mise x {PG_TOOL} -- pg_ctl -D <fresh-tmpdir> -o '-p {PORT} "
            "-c listen_addresses=127.0.0.1' -w start",
            f"python -m alembic stamp {PARENT_REVISION}",
            f"python -m alembic upgrade {REVISION}",
            f"python -m alembic downgrade {PARENT_REVISION}",
        ],
    }
    service = TenantMessagingService()
    try:
        with psycopg.connect(plain_url, autocommit=True) as conn:
            server = conn.execute("SELECT inet_server_addr()::text, current_database()").fetchone()
            assert server[1] == prelaunch_db["db_name"]
            assert server[0].startswith("127.0.0.1")
            evidence["server_addr"] = server[0]
            evidence["revision_before_stamp"] = _revision(conn)
            _install_parent(conn)

        stamped = _run_alembic(sync_url, "stamp", PARENT_REVISION)
        assert stamped.returncode == 0, stamped.stderr
        upgraded = _run_alembic(sync_url, "upgrade", REVISION)
        assert upgraded.returncode == 0, upgraded.stderr
        evidence["alembic_upgrade_tail"] = upgraded.stderr.strip().splitlines()[-4:]

        with psycopg.connect(plain_url, autocommit=True) as conn:
            evidence["revision_after_upgrade"] = _revision(conn)
            evidence["message_types_after_upgrade"] = _message_types(conn)
            evidence["indexes_after_upgrade"] = _lock_indexes(conn)
            evidence["constraint_after_upgrade"] = _constraint(conn)
            assert evidence["revision_after_upgrade"] == REVISION
            for name, (data_type, length) in evidence["message_types_after_upgrade"].items():
                assert data_type == "text", name
                assert length is None
            for index_name in (
                "idx_email_send_locks_accepted_pending",
                "idx_email_send_locks_dispatching",
                "idx_email_send_locks_unsent_locked",
                "idx_email_send_locks_finalize_due",
            ):
                assert index_name in evidence["indexes_after_upgrade"]
            assert "accepted_pending" in evidence["constraint_after_upgrade"]
            assert "uncertain" in evidence["constraint_after_upgrade"]

            default_plan = _seed_plan(conn, "default")
            other_plan = _seed_plan(conn, "instance_b")
            pending = []
            for index in range(21):
                message_id = SYNTHETIC_ID if index == 20 else f"pending-{index:02d}-example"
                pending.append(
                    _add_enrollment(
                        conn,
                        default_plan,
                        status="accepted_pending",
                        with_email=True,
                        message_id=message_id,
                        accepted_at=ACCEPTED_AT + timedelta(seconds=index),
                        started_at=NOW - timedelta(minutes=40),
                    )
                )
            stored = conn.execute(
                """
                SELECT engagelab_message_id, length(engagelab_message_id),
                       tableoid::regclass::text
                FROM emails WHERE id = %s
                """,
                (pending[-1]["email_id"],),
            ).fetchone()
            evidence["synthetic_id_length"] = stored[1]
            evidence["synthetic_id_equal"] = stored[0] == SYNTHETIC_ID
            evidence["synthetic_partition"] = stored[2]
            assert stored[0] == SYNTHETIC_ID
            assert stored[1] == 107
            assert stored[0] != SYNTHETIC_ID[:100]
            assert stored[2] == "emails_p_2026_10"

            stale_at = NOW - timedelta(minutes=31)
            unsent = _add_enrollment(
                conn,
                default_plan,
                status="locked",
                locked_at=stale_at,
                quota_date=USAGE_DATE,
            )
            legacy = _add_enrollment(
                conn,
                default_plan,
                status="locked",
                locked_at=stale_at,
            )
            dispatching = _add_enrollment(
                conn,
                default_plan,
                status="dispatching",
                locked_at=stale_at,
                started_at=stale_at,
                quota_date=USAGE_DATE,
            )
            uncertain = _add_enrollment(
                conn,
                default_plan,
                status="uncertain",
                locked_at=stale_at,
                started_at=stale_at,
            )
            other_unsent = _add_enrollment(
                conn,
                other_plan,
                status="locked",
                locked_at=stale_at,
                quota_date=USAGE_DATE,
            )

        first_engine = _engine(async_url)
        second_engine = _engine(async_url)
        try:
            locked = asyncio.Event()
            release = asyncio.Event()
            first_page, second_page = await asyncio.wait_for(
                asyncio.gather(
                    _claim_first(first_engine, service, locked, release),
                    _claim_second(second_engine, service, locked, release),
                ),
                timeout=20,
            )
        finally:
            await first_engine.dispose()
            await second_engine.dispose()
        first_ids = {row["email_id"] for row in first_page}
        second_ids = {row["email_id"] for row in second_page}
        expected_ids = {row["email_id"] for row in pending}
        evidence["skip_locked"] = {
            "sizes": sorted([len(first_ids), len(second_ids)]),
            "disjoint": first_ids.isdisjoint(second_ids),
            "covers_pending": first_ids | second_ids == expected_ids,
        }
        assert first_ids.isdisjoint(second_ids)
        assert first_ids | second_ids == expected_ids
        assert sorted(evidence["skip_locked"]["sizes"]) == [1, 20]
        singleton = first_page if len(first_page) == 1 else second_page
        assert singleton[0]["email_id"] == pending[-1]["email_id"]

        with psycopg.connect(plain_url, autocommit=True) as conn:
            conn.execute(
                """
                UPDATE email_send_locks
                SET finalize_not_before = NULL
                WHERE status = 'accepted_pending'
                """
            )
            race = _add_enrollment(
                conn,
                default_plan,
                status="accepted_pending",
                with_email=True,
                message_id="race-receipt-example",
                accepted_at=ACCEPTED_AT,
                started_at=NOW,
            )

        payload = {"engagelab_message_id": "race-receipt-example", "sent_at": NOW}
        due_at = ACCEPTED_AT + timedelta(days=3)

        async def _finalize_pair(email_id: str, body: dict) -> list[dict]:
            left = _engine(async_url)
            right = _engine(async_url)
            barrier = asyncio.Barrier(2)

            async def _finalize(engine):
                await asyncio.wait_for(barrier.wait(), timeout=10)
                async with engine.begin() as conn:
                    return await service.mark_email_sent(conn, email_id=email_id, payload=body)

            try:
                return await asyncio.wait_for(
                    asyncio.gather(_finalize(left), _finalize(right)),
                    timeout=20,
                )
            finally:
                await left.dispose()
                await right.dispose()

        with psycopg.connect(plain_url, autocommit=True) as conn:
            next_step_kept = conn.execute(
                "SELECT delay_days FROM sequence_steps WHERE id = %s",
                (default_plan["step_two"],),
            ).fetchone()
        assert next_step_kept == (3,)
        outcomes = await _finalize_pair(race["email_id"], payload)
        duplicates = sorted(bool(item.get("duplicate")) for item in outcomes)
        repeat_engine = _engine(async_url)
        try:
            async with repeat_engine.begin() as conn:
                repeated = await service.mark_email_sent(
                    conn, email_id=race["email_id"], payload=payload
                )
        finally:
            await repeat_engine.dispose()
        with psycopg.connect(plain_url, autocommit=True) as conn:
            sent_count = conn.execute(
                "SELECT sent_count FROM sending_plans WHERE id = %s",
                (race["plan_id"],),
            ).fetchone()[0]
            enrollment = conn.execute(
                """
                SELECT current_step, last_step_sent_at, next_step_due_at, completed_at
                FROM sequence_enrollments WHERE id = %s
                """,
                (race["enrollment_id"],),
            ).fetchone()
            email_sent_at = conn.execute(
                "SELECT sent_at, status FROM emails WHERE id = %s",
                (race["email_id"],),
            ).fetchone()
        evidence["next_step_finalize"] = {
            "path": "non_final",
            "step_two_delay_days": next_step_kept[0],
            "duplicate_flags": duplicates,
            "repeat_duplicate": bool(repeated.get("duplicate")),
            "sent_count": sent_count,
            "current_step": enrollment[0],
            "last_step_sent_at": enrollment[1],
            "next_step_due_at": enrollment[2],
            "completed_at": enrollment[3],
            "sent_at": email_sent_at[0],
            "email_status": email_sent_at[1],
            "accepted_at_utc": ACCEPTED_AT.isoformat(),
            "recovery_clock_utc": NOW.isoformat(),
        }
        assert duplicates == [False, True]
        assert repeated.get("duplicate") is True
        assert sent_count == 1
        assert enrollment[0] == 2
        assert enrollment[1] == ACCEPTED_AT
        assert enrollment[2] == due_at
        assert enrollment[2] != NOW + timedelta(days=3)
        assert enrollment[3] is None
        assert email_sent_at[0] == ACCEPTED_AT
        assert email_sent_at[0] != NOW
        assert email_sent_at[1] == "sent"

        with psycopg.connect(plain_url, autocommit=True) as conn:
            conn.execute(
                """
                CREATE FUNCTION prelaunch_reject_pending() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                  IF NEW.status = 'sent'
                     AND OLD.provider_message_id LIKE 'pending-%%' THEN
                    RAISE EXCEPTION 'synthetic finalize failure';
                  END IF;
                  RETURN NEW;
                END $$
                """
            )
            conn.execute(
                """
                CREATE TRIGGER prelaunch_reject_pending
                BEFORE UPDATE ON email_send_locks
                FOR EACH ROW EXECUTE FUNCTION prelaunch_reject_pending()
                """
            )
        provider = _NoSend()
        logs: list[dict] = []
        workers = [
            SendingWorker(
                service=service,
                provider=provider,
                clock=lambda: NOW,
                sleep=lambda _seconds: asyncio.sleep(0),
                log_sink=logs.append,
            )
            for _ in range(2)
        ]
        worker_engines = [_engine(async_url), _engine(async_url)]
        worker_barrier = asyncio.Barrier(2)

        async def _recover(index: int) -> int:
            await asyncio.wait_for(worker_barrier.wait(), timeout=10)
            return await workers[index]._finalize_pending(worker_engines[index])

        try:
            finalized = await asyncio.wait_for(
                asyncio.gather(_recover(0), _recover(1)),
                timeout=20,
            )
        finally:
            for engine in worker_engines:
                await engine.dispose()
        with psycopg.connect(plain_url, autocommit=True) as conn:
            newest_status = conn.execute(
                "SELECT status FROM email_send_locks WHERE id = %s",
                (pending[-1]["lock_id"],),
            ).fetchone()[0]
            deferred = conn.execute(
                """
                SELECT count(*) FROM email_send_locks
                WHERE provider_message_id LIKE 'pending-%%'
                  AND status = 'accepted_pending'
                  AND finalize_not_before = %s
                """,
                (NOW + timedelta(seconds=60),),
            ).fetchone()[0]
            plan_sent = conn.execute(
                "SELECT sent_count FROM sending_plans WHERE id = %s",
                (default_plan["plan_id"],),
            ).fetchone()[0]
            newest_email = conn.execute(
                """
                SELECT e.sent_at, length(e.engagelab_message_id), se.completed_at,
                       se.current_step, se.next_step_due_at, se.last_step_sent_at
                FROM emails e
                JOIN sequence_enrollments se ON se.id = e.enrollment_id
                WHERE e.id = %s
                """,
                (pending[-1]["email_id"],),
            ).fetchone()
        newest_accepted = ACCEPTED_AT + timedelta(seconds=20)
        evidence["workers"] = {
            "path": "non_final",
            "finalized": list(finalized),
            "send_calls": provider.calls,
            "newest_status": newest_status,
            "deferred_pending": deferred,
            "plan_sent_count": plan_sent,
            "newest_sent_at": newest_email[0],
            "newest_completed_at": newest_email[2],
            "newest_current_step": newest_email[3],
            "newest_next_step_due_at": newest_email[4],
            "newest_last_step_sent_at": newest_email[5],
            "log_contains_raw_id": any(SYNTHETIC_ID in json.dumps(item) for item in logs),
        }
        assert sum(finalized) == 1
        assert provider.calls == []
        assert newest_status == "sent"
        assert deferred == 20
        assert plan_sent == 2
        assert newest_email[0] == newest_accepted
        assert newest_email[0] != NOW
        assert newest_email[1] == 107
        assert newest_email[2] is None
        assert newest_email[3] == 2
        assert newest_email[4] == newest_accepted + timedelta(days=3)
        assert newest_email[5] == newest_accepted
        assert evidence["workers"]["log_contains_raw_id"] is False

        with psycopg.connect(plain_url, autocommit=True) as conn:
            last_plan = _seed_plan(
                conn,
                "default",
                with_next_step=False,
                contact_seq=8000,
            )
            last_row = _add_enrollment(
                conn,
                last_plan,
                status="accepted_pending",
                with_email=True,
                message_id="last-step-receipt",
                accepted_at=ACCEPTED_AT,
                started_at=NOW,
            )
        last_outcomes = await _finalize_pair(
            last_row["email_id"],
            {"engagelab_message_id": "last-step-receipt", "sent_at": NOW},
        )
        last_duplicates = sorted(bool(item.get("duplicate")) for item in last_outcomes)
        with psycopg.connect(plain_url, autocommit=True) as conn:
            last_sent = conn.execute(
                "SELECT sent_count FROM sending_plans WHERE id = %s",
                (last_plan["plan_id"],),
            ).fetchone()[0]
            last_enrollment = conn.execute(
                """
                SELECT current_step, last_step_sent_at, next_step_due_at, completed_at, status
                FROM sequence_enrollments WHERE id = %s
                """,
                (last_row["enrollment_id"],),
            ).fetchone()
        evidence["last_step_finalize"] = {
            "duplicate_flags": last_duplicates,
            "sent_count": last_sent,
            "current_step": last_enrollment[0],
            "last_step_sent_at": last_enrollment[1],
            "next_step_due_at": last_enrollment[2],
            "completed_at": last_enrollment[3],
            "status": last_enrollment[4],
            "send_calls": provider.calls,
        }
        assert last_duplicates == [False, True]
        assert last_sent == 1
        assert last_enrollment[0] == 1
        assert last_enrollment[1] == ACCEPTED_AT
        assert last_enrollment[2] is None
        assert last_enrollment[3] == ACCEPTED_AT
        assert last_enrollment[4] == "completed"
        assert provider.calls == []

        with psycopg.connect(plain_url, autocommit=True) as conn:
            lease_row = _add_enrollment(
                conn,
                default_plan,
                status="accepted_pending",
                with_email=True,
                message_id="lease-receipt-example",
                accepted_at=ACCEPTED_AT + timedelta(minutes=5),
                started_at=NOW,
            )
        lease_engine = _engine(async_url)
        async with lease_engine.begin() as conn:
            leased = await service.list_accepted_pending(
                conn,
                limit=20,
                as_of=NOW,
                lease_until=NOW + timedelta(seconds=15),
            )
        await lease_engine.dispose()
        during = _engine(async_url)
        async with during.begin() as conn:
            hidden = await service.list_accepted_pending(conn, limit=20, as_of=NOW)
        await during.dispose()
        after = _engine(async_url)
        async with after.begin() as conn:
            restored = await service.list_accepted_pending(
                conn,
                limit=20,
                as_of=NOW + timedelta(seconds=16),
            )
        await after.dispose()
        evidence["lease_expiry"] = {
            "leased_ids": [row["email_id"] for row in leased],
            "hidden_while_leased": [row["email_id"] for row in hidden],
            "visible_after_expiry": [row["email_id"] for row in restored],
        }
        assert [row["email_id"] for row in leased] == [lease_row["email_id"]]
        assert hidden == []
        assert [row["email_id"] for row in restored] == [lease_row["email_id"]]

        quota_engine = _engine(async_url)
        async with quota_engine.begin() as conn:
            released = await service.release_unsent_locks(conn, as_of=NOW, stale_minutes=30)
            released_again = await service.release_unsent_locks(
                conn, as_of=NOW, stale_minutes=30
            )
        await quota_engine.dispose()
        with psycopg.connect(plain_url, autocommit=True) as conn:
            default_reserved = conn.execute(
                """
                SELECT reserved_count FROM domain_daily_usage
                WHERE domain_id = %s AND usage_date = %s
                """,
                (default_plan["domain_id"], USAGE_DATE),
            ).fetchone()[0]
            other_reserved = conn.execute(
                """
                SELECT reserved_count FROM domain_daily_usage
                WHERE domain_id = %s AND usage_date = %s
                """,
                (other_plan["domain_id"], USAGE_DATE),
            ).fetchone()[0]
            wrong_day = conn.execute(
                """
                SELECT count(*) FROM domain_daily_usage
                WHERE domain_id = %s AND usage_date = %s
                """,
                (default_plan["domain_id"], NOW.date()),
            ).fetchone()[0]
            statuses = {
                key: conn.execute(
                    "SELECT status FROM email_send_locks WHERE id = %s",
                    (row["lock_id"],),
                ).fetchone()[0]
                for key, row in {
                    "unsent": unsent,
                    "legacy": legacy,
                    "dispatching": dispatching,
                    "uncertain": uncertain,
                    "other": other_unsent,
                }.items()
            }
        evidence["quota"] = {
            "recovered": released["recovered_count"],
            "recovered_again": released_again["recovered_count"],
            "default_reserved": default_reserved,
            "other_reserved": other_reserved,
            "recovery_day_rows": wrong_day,
            "statuses": statuses,
        }
        assert released["recovered_count"] == 1
        assert released["enrollment_ids"] == [unsent["enrollment_id"]]
        assert released_again["recovered_count"] == 0
        assert default_reserved == 3
        assert other_reserved == 4
        assert wrong_day == 0
        assert statuses == {
            "unsent": "released",
            "legacy": "locked",
            "dispatching": "dispatching",
            "uncertain": "uncertain",
            "other": "locked",
        }

        refused = _run_alembic(sync_url, "downgrade", PARENT_REVISION)
        with psycopg.connect(plain_url, autocommit=True) as conn:
            kept = conn.execute(
                "SELECT engagelab_message_id FROM emails WHERE id = %s",
                (pending[-1]["email_id"],),
            ).fetchone()[0]
            evidence["downgrade_refused"] = {
                "returncode": refused.returncode,
                "mentions_guard": "cannot downgrade" in refused.stderr,
                "revision": _revision(conn),
                "synthetic_kept": kept == SYNTHETIC_ID,
            }
        assert refused.returncode != 0
        assert evidence["downgrade_refused"]["mentions_guard"] is True
        assert evidence["downgrade_refused"]["revision"] == REVISION
        assert kept == SYNTHETIC_ID

        with psycopg.connect(plain_url, autocommit=True) as conn:
            conn.execute("DROP TRIGGER prelaunch_reject_pending ON email_send_locks")
            conn.execute("DROP FUNCTION prelaunch_reject_pending()")
            conn.execute("DELETE FROM email_send_locks")
            conn.execute("DELETE FROM emails")
            survivor = _add_enrollment(
                conn,
                default_plan,
                status="locked",
                with_email=True,
                message_id=SHORT_ID,
            )
            conn.execute(
                """
                UPDATE email_send_locks
                SET provider_message_id = NULL,
                    provider_accepted_at = NULL,
                    dispatch_started_at = NULL,
                    quota_usage_date = NULL,
                    finalize_not_before = NULL
                WHERE id = %s
                """,
                (survivor["lock_id"],),
            )
        emptied = _run_alembic(sync_url, "downgrade", PARENT_REVISION)
        assert emptied.returncode == 0, emptied.stderr
        with psycopg.connect(plain_url, autocommit=True) as conn:
            evidence["after_empty_downgrade"] = {
                "revision": _revision(conn),
                "message_types": _message_types(conn),
                "constraint": _constraint(conn),
                "new_indexes": [
                    name
                    for name in _lock_indexes(conn)
                    if name.startswith("idx_email_send_locks_")
                ],
                "survivor_id": conn.execute(
                    "SELECT engagelab_message_id FROM emails WHERE id = %s",
                    (survivor["email_id"],),
                ).fetchone()[0],
                "survivor_status": conn.execute(
                    "SELECT status FROM email_send_locks WHERE id = %s",
                    (survivor["lock_id"],),
                ).fetchone()[0],
            }
        assert evidence["after_empty_downgrade"]["revision"] == PARENT_REVISION
        for data_type, length in evidence["after_empty_downgrade"]["message_types"].values():
            assert data_type == "character varying"
            assert length == 100
        assert "accepted_pending" not in evidence["after_empty_downgrade"]["constraint"]
        assert evidence["after_empty_downgrade"]["new_indexes"] == []
        assert evidence["after_empty_downgrade"]["survivor_id"] == SHORT_ID
        assert evidence["after_empty_downgrade"]["survivor_status"] == "locked"

        again = _run_alembic(sync_url, "upgrade", REVISION)
        assert again.returncode == 0, again.stderr
        with psycopg.connect(plain_url, autocommit=True) as conn:
            evidence["revision_after_reupgrade"] = _revision(conn)
            assert evidence["revision_after_reupgrade"] == REVISION
            assert _message_types(conn)["emails"] == ["text", None]
            conn.execute(
                """
                UPDATE email_send_locks
                SET status = 'uncertain', dispatch_started_at = %s
                WHERE id = %s
                """,
                (NOW, survivor["lock_id"]),
            )
        refused_uncertain = _run_alembic(sync_url, "downgrade", PARENT_REVISION)
        with psycopg.connect(plain_url, autocommit=True) as conn:
            uncertain_row = conn.execute(
                """
                SELECT status, dispatch_started_at IS NOT NULL
                FROM email_send_locks WHERE id = %s
                """,
                (survivor["lock_id"],),
            ).fetchone()
            evidence["uncertain_downgrade"] = {
                "returncode": refused_uncertain.returncode,
                "mentions_guard": "cannot downgrade" in refused_uncertain.stderr,
                "revision": _revision(conn),
                "status": uncertain_row[0],
                "started_at_kept": uncertain_row[1],
                "short_id": conn.execute(
                    "SELECT engagelab_message_id FROM emails WHERE id = %s",
                    (survivor["email_id"],),
                ).fetchone()[0],
            }
        assert refused_uncertain.returncode != 0
        assert evidence["uncertain_downgrade"]["mentions_guard"] is True
        assert evidence["uncertain_downgrade"]["revision"] == REVISION
        assert uncertain_row == ("uncertain", True)
        assert evidence["uncertain_downgrade"]["short_id"] == SHORT_ID
        evidence["result"] = "passed"
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        _write_evidence(evidence)
