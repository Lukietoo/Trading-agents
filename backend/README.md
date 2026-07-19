# Dashboard backend

FastAPI service exposing the dashboard snapshot assembled from the Alpaca
paper API.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run

Credentials come from environment variables (see `../.env.example`):

```sh
set -a; source ../.env; set +a
.venv/bin/uvicorn app.main:app_from_env --factory --port 8000
```

The frontend dev server proxies `/api` to `127.0.0.1:8000`.

## Test

```sh
.venv/bin/pytest
```

Tests run against the app with a fake Alpaca client — no network.
