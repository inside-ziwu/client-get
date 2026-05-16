from pathlib import Path
import subprocess


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_prod_db_to_local.sh"


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )


def test_help_documents_remote_url_resolution_order() -> None:
    result = run_script("--help")

    assert result.returncode == 0
    assert "CLIENTGET_PROD_DATABASE_URL" in result.stdout
    assert "~/.clientget/prod-db-url" in result.stdout


def test_dry_run_rejects_missing_remote_url() -> None:
    result = run_script(
        "--dry-run",
        env={
            "HOME": "/tmp/clientget-sync-script-test-no-config",
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
    )

    assert result.returncode != 0
    assert "Remote URL not configured" in result.stderr


def test_dry_run_refuses_remote_url_that_points_to_localhost() -> None:
    result = run_script(
        "--dry-run",
        "--remote-url",
        "postgresql://postgres:postgres@localhost:5432/clientget",
    )

    assert result.returncode != 0
    assert "Remote URL points to localhost" in result.stderr
