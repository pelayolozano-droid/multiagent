"""Persistencia en JSON local: data/empresas/<id>.json, data/memoria.json, data/custom.json."""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
EMPRESAS = DATA / "empresas"


def new_id(prefix: str) -> str:
    return f"{prefix}{int(time.time() * 1000):x}{secrets.token_hex(2)}"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def list_companies() -> list[dict]:
    if not EMPRESAS.exists():
        return []
    out = [_read(p, None) for p in EMPRESAS.glob("*.json")]
    return sorted([c for c in out if c], key=lambda c: c.get("actualizado", ""), reverse=True)


def load_company(cid: str) -> dict | None:
    return _read(EMPRESAS / f"{cid}.json", None)


def save_company(p: dict) -> None:
    p["actualizado"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _write(EMPRESAS / f"{p['id']}.json", p)


def delete_company(cid: str) -> None:
    (EMPRESAS / f"{cid}.json").unlink(missing_ok=True)


def load_memoria() -> dict:
    return _read(DATA / "memoria.json", {})


def save_memoria(m: dict) -> None:
    _write(DATA / "memoria.json", m)


def load_customs() -> list[dict]:
    return _read(DATA / "custom.json", [])


def save_customs(c: list[dict]) -> None:
    _write(DATA / "custom.json", c)
