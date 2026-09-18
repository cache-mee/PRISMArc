"""Windows-safe local dev entrypoint for the FastAPI app.

Running ``uvicorn app.main:app`` (or ``python -m uvicorn app.main:app``) directly on
Windows fails every DB call with::

    psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async
    mode.

The installed uvicorn's asyncio loop factory (``uvicorn/loops/asyncio.py``) hardcodes
``asyncio.ProactorEventLoop`` on ``win32``, which psycopg's async driver can't run on.
Setting ``UVICORN_LOOP=asyncio:SelectorEventLoop`` in ``.env`` does **not** fix this:
pydantic-settings' ``env_file`` loading only feeds values into ``Settings`` — it never
calls ``os.environ.update()`` — so uvicorn's CLI (which reads that var via its own
``auto_envvar_prefix="UVICORN"``) never sees it. Passing ``loop=`` directly to
``uvicorn.run()`` here sidesteps that entirely.

Linux/the Docker image (see ``Dockerfile``) don't hit this — ``ProactorEventLoop`` is
Windows-only — so this script is for local Windows development only; it isn't part of
the container's start command.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        loop="asyncio:SelectorEventLoop",
    )
