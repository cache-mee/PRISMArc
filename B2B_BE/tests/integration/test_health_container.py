"""Integration test: build the real Dockerfile, run the container, and hit
GET /health over a real TCP socket/HTTP request — not the in-process
TestClient used by tests/test_health.py.

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
STARTUP_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 0.5


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1]


@pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="Docker is not available in this environment",
)
def test_health_endpoint_via_built_container() -> None:
    build_result = subprocess.run(
        ["docker", "build", "-t", IMAGE_TAG, str(DOCKERFILE_DIR)],
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_SECONDS,
    )
    assert build_result.returncode == 0, (
        f"docker build failed (exit {build_result.returncode}):\n"
        f"stdout:\n{build_result.stdout}\nstderr:\n{build_result.stderr}"
    )

    container_name = f"b2b-be-integration-{uuid.uuid4().hex[:8]}"
    host_port = _free_port()

    run_result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{host_port}:8000",
            IMAGE_TAG,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run_result.returncode == 0, (
        f"docker run failed (exit {run_result.returncode}):\n"
        f"stdout:\n{run_result.stdout}\nstderr:\n{run_result.stderr}"
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

        assert response is not None, (
            f"container never responded on {url} within "
            f"{STARTUP_TIMEOUT_SECONDS}s (last error: {last_error})"
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
