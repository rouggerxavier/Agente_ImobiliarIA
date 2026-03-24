"""Cliente CLI simples para conversar com o backend local sem Streamlit."""

from __future__ import annotations

import os
import uuid
from typing import Any

import requests


def send_message(
    session_id: str,
    message: str,
    name: str | None = None,
    backend_url: str | None = None,
    api_key: str | None = None,
) -> str:
    """Envia mensagem ao backend FastAPI e retorna o texto de resposta."""
    base_url = (backend_url or os.getenv("BACKEND_URL") or "http://localhost:8000").rstrip("/")
    payload: dict[str, Any] = {
        "session_id": session_id,
        "message": message,
        "name": name,
    }
    headers = {"Content-Type": "application/json"}
    token = api_key or os.getenv("WEBHOOK_API_KEY")
    if token:
        headers["X-API-Key"] = token

    try:
        resp = requests.post(f"{base_url}/webhook", json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data.get("reply") or data.get("response") or data.get("message") or str(data)
        return str(data)
    except Exception as exc:
        return f"Erro ao contatar o backend: {exc}"


def run_cli() -> None:
    """Loop interativo em terminal para testes locais rápidos."""
    session_id = str(uuid.uuid4())
    print("Chat imobiliário (CLI) iniciado.")
    print("Digite 'sair' para encerrar.")
    print(f"session_id: {session_id}")
    print()

    while True:
        user_message = input("Você: ").strip()
        if not user_message:
            continue
        if user_message.lower() in {"sair", "exit", "quit"}:
            print("Encerrado.")
            break

        reply = send_message(session_id=session_id, message=user_message)
        print(f"Agente: {reply}")
        print()


if __name__ == "__main__":
    run_cli()
