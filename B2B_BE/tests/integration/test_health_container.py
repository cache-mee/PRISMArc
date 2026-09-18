"""Integration test: build the real Dockerfile, run the container against a
real disposable Postgres, and hit GET /health over a real TCP socket/HTTP
request — not the in-process TestClient used by tests/test_health.py.

The container's entrypoint runs `alembic upgrade head` before serving
(B2B_BE/Dockerfile), so a real Postgres is required here — a mocked or
absent DB would make migrations fail before /health is ever reachable.

Covers: AC2 (Dockerfile builds the service) extended to AC6 (GET /health
returns 200) over the packaged-container/network boundary, per the approved
integration-test-plan.md.
"""

import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE_DIR = REPO_ROOT / "B2B_BE"
IMAGE_TAG = "b2b-be:integration-test"
BUILD_TIMEOUT_SECONDS = 300
PG_READY_TIMEOUT_SECONDS = 30
STARTUP_TIMEOUT_SECONDS = 45
POLL_INTERVAL_SECONDS = 0.5


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1]


def _run(*args: str, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)


@pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="Docker is not available in this environment",
)
def test_health_endpoint_via_built_container() -> None:
    run_id = uuid.uuid4().hex[:8]
    network_name = f"b2b-be-test-net-{run_id}"
    pg_container_name = f"b2b-be-test-pg-{run_id}"
    app_container_name = f"b2b-be-integration-{run_id}"
    host_port = _free_port()

    network_result = _run("docker", "network", "create", network_name, timeout=30)
    assert network_result.returncode == 0, (
        f"docker network create failed (exit {network_result.returncode}):\n"
        f"stderr:\n{network_result.stderr}"
    )

    try:
        pg_run_result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            pg_container_name,
            "--network",
            network_name,
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_DB=testdb",
            "postgres:16-alpine",
            timeout=60,
        )
        assert pg_run_result.returncode == 0, (
            f"docker run (postgres) failed (exit {pg_run_result.returncode}):\n"
            f"stderr:\n{pg_run_result.stderr}"
        )

        deadline = time.monotonic() + PG_READY_TIMEOUT_SECONDS
        pg_ready = False
        while time.monotonic() < deadline:
            ready_check = _run(
                "docker",
                "exec",
                pg_container_name,
                "pg_isready",
                "-U",
                "postgres",
                timeout=10,
            )
            if ready_check.returncode == 0:
                pg_ready = True
                break
            time.sleep(POLL_INTERVAL_SECONDS)
        assert (
            pg_ready
        ), f"postgres did not become ready within {PG_READY_TIMEOUT_SECONDS}s"

        build_result = _run(
            "docker",
            "build",
            "-t",
            IMAGE_TAG,
            str(DOCKERFILE_DIR),
            timeout=BUILD_TIMEOUT_SECONDS,
        )
        assert build_result.returncode == 0, (
            f"docker build failed (exit {build_result.returncode}):\n"
            f"stdout:\n{build_result.stdout}\nstderr:\n{build_result.stderr}"
        )

        database_url = (
            f"postgresql+psycopg://postgres:postgres@{pg_container_name}:5432/testdb"
        )
        app_run_result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            app_container_name,
            "--network",
            network_name,
            "-p",
            f"{host_port}:8000",
            "-e",
            f"DATABASE_URL={database_url}",
            IMAGE_TAG,
            timeout=60,
        )
        assert app_run_result.returncode == 0, (
            f"docker run (backend) failed (exit {app_run_result.returncode}):\n"
            f"stderr:\n{app_run_result.stderr}"
        )

        try:
            url = f"http://localhost:{host_port}/health"
            deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
            last_error: Exception | None = None
            response: httpx.Response | None = None

            while time.monotonic() < deadline:
                try:
                    response = httpx.get(url, timeout=2.0)
                    break
                except httpx.HTTPError as exc:
                    last_error = exc
                    time.sleep(POLL_INTERVAL_SECONDS)

            if response is None:
                logs = _run("docker", "logs", app_container_name, timeout=10)
                raise AssertionError(
                    f"container never responded on {url} within "
                    f"{STARTUP_TIMEOUT_SECONDS}s (last error: {last_error})\n"
                    f"container logs:\n{logs.stdout}\n{logs.stderr}"
                )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        finally:
            _run("docker", "rm", "-f", app_container_name, timeout=30)
    finally:
        _run("docker", "rm", "-f", pg_container_name, timeout=30)
        _run("docker", "network", "rm", network_name, timeout=30)
