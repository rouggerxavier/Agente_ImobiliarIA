"""Endpoints de contato e newsletter."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["contato"])

_DATA_DIR = Path("data")
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_CONTACT_LOG = _DATA_DIR / "contact_messages.jsonl"
_NEWSLETTER_LOG = _DATA_DIR / "newsletter_subscriptions.jsonl"


class ContactRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=180)
    telefone: str = Field(..., min_length=8, max_length=40)
    mensagem: str = Field(..., min_length=5, max_length=4000)


class NewsletterRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=180)


def _append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


@router.post("/contato", status_code=status.HTTP_201_CREATED)
def enviar_contato(body: ContactRequest) -> dict:
    contact_id = f"contact_{uuid.uuid4().hex[:12]}"
    payload = {
        "id": contact_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "nome": body.nome.strip(),
        "email": body.email,
        "telefone": body.telefone.strip(),
        "mensagem": body.mensagem.strip(),
        "canal": "site",
    }
    _append_jsonl(_CONTACT_LOG, payload)
    return {"ok": True, "id": contact_id}


@router.post("/newsletter", status_code=status.HTTP_201_CREATED)
def cadastrar_newsletter(body: NewsletterRequest) -> dict:
    subscription_id = f"newsletter_{uuid.uuid4().hex[:12]}"
    payload = {
        "id": subscription_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "nome": body.nome.strip(),
        "email": body.email,
        "canal": "site",
    }
    _append_jsonl(_NEWSLETTER_LOG, payload)
    return {"ok": True, "id": subscription_id}
