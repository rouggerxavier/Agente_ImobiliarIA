"""Enrich catalog items using property detail pages from grankasa.com.br.

Usage:
  python scripts/enrich_grankasa_catalog.py
  python scripts/enrich_grankasa_catalog.py --limit 20 --sleep 0.1
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from html import unescape
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "grankasa_catalog_audit.json"
OUTPUT_FILE = ROOT / "data" / "grankasa_catalog_enriched.json"
META_FILE = ROOT / "data" / "grankasa_catalog_enriched_meta.json"

LABEL_MAP = {
    "tipo": "tipo",
    "condominio": "condominio",
    "iptu": "iptu",
    "area": "area",
    "quartos": "quartos",
    "suites": "suites",
    "salas": "salas",
    "banheiros": "banheiros",
    "dependencias": "dependencias",
    "vagas": "vagas",
    "ano de construcao": "ano_construcao",
    "numero de andares": "numero_andares",
    "elevadores": "elevadores",
}


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip()


def _clean_html_text(raw: str | None) -> str:
    if not raw:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", raw)
    return _normalize(no_tags)


def _extract_title(norm_html: str) -> str:
    match = re.search(r'<div class="header-imovel">.*?<h2>(.*?)</h2>', norm_html, re.I | re.S)
    if not match:
        return ""
    return _clean_html_text(match.group(1))


def _extract_description(norm_html: str) -> str:
    match = re.search(r'<div class="descricao">\s*<p>(.*?)</p>', norm_html, re.I | re.S)
    if not match:
        return ""
    text = _clean_html_text(match.group(1))
    return text


def _extract_price(norm_html: str) -> str:
    match = re.search(r'<div class="valor">\s*(.*?)\s*</div>', norm_html, re.I | re.S)
    if not match:
        return ""
    return _clean_html_text(match.group(1))


def _extract_images(raw_html: str, codigo: str) -> list[str]:
    pattern = rf"https://cdn\.vistahost\.com\.br/grankasa/vista\.imobi/fotos/{re.escape(codigo)}/[^\"']+"
    urls = re.findall(pattern, raw_html, re.I)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _extract_video_url(raw_html: str) -> str | None:
    match = re.search(r'<iframe[^>]+src="([^"]*(?:youtube|youtu\.be)[^"]*)"', raw_html, re.I)
    if not match:
        return None
    return match.group(1).strip()


def _extract_map_url(raw_html: str) -> str | None:
    match = re.search(r'<iframe[^>]+src="([^"]*maps\.google[^"]*)"', raw_html, re.I)
    if not match:
        return None
    return match.group(1).strip()


def _extract_label_values(norm_html: str) -> dict[str, str]:
    found = re.findall(r"<li>\s*([^:<]{1,80}):\s*<strong>(.*?)</strong>\s*</li>", norm_html, re.I | re.S)
    data: dict[str, str] = {}
    for raw_label, raw_value in found:
        label = _normalize(raw_label).lower()
        value = _clean_html_text(raw_value)
        canonical = LABEL_MAP.get(label)
        if canonical:
            data[canonical] = value
    return data


def _extract_code(norm_html: str, fallback: str) -> str:
    match = re.search(r"Cod\.\s*(\d+)", norm_html, re.I)
    if match:
        return match.group(1).strip()
    return fallback


def _split_location(title: str) -> tuple[str | None, str | None, str | None]:
    clean = _normalize(title)
    if " - " not in clean:
        return None, None, None
    bairro, uf = clean.split(" - ", 1)
    bairro = bairro.strip() or None
    uf = uf.strip() or None
    cidade = "Rio de Janeiro" if uf and uf.upper() == "RJ" else None
    return bairro, cidade, uf


def enrich_item(session: requests.Session, item: dict, timeout: float) -> tuple[dict, str | None]:
    url = item.get("url_detalhada")
    if not url:
        return item, "missing_url"

    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return item, f"request_error:{exc.__class__.__name__}"

    raw_html = resp.text
    norm_html = _normalize(raw_html)

    code = _extract_code(norm_html, _normalize(str(item.get("codigo") or "")))
    title = _extract_title(norm_html) or _normalize(item.get("titulo"))
    description = _extract_description(norm_html)
    price = _extract_price(norm_html) or _normalize(item.get("preco"))
    labels = _extract_label_values(norm_html)
    images = _extract_images(raw_html, code)
    video_url = _extract_video_url(raw_html)
    map_url = _extract_map_url(raw_html)
    bairro, cidade, uf = _split_location(title)

    enriched = dict(item)
    enriched.update(
        {
            "codigo": code or item.get("codigo"),
            "titulo": title or item.get("titulo"),
            "preco": price or item.get("preco"),
            "descricao_longa": description or item.get("descricao_longa"),
            "tipo": labels.get("tipo") or item.get("tipo"),
            "condominio": labels.get("condominio") or item.get("condominio"),
            "iptu": labels.get("iptu") or item.get("iptu"),
            "area": labels.get("area") or item.get("area"),
            "quartos": labels.get("quartos") or item.get("quartos"),
            "suites": labels.get("suites") or item.get("suites"),
            "salas": labels.get("salas") or item.get("salas"),
            "banheiros": labels.get("banheiros") or item.get("banheiros"),
            "dependencias": labels.get("dependencias") or item.get("dependencias"),
            "vagas": labels.get("vagas") or item.get("vagas"),
            "ano_construcao": labels.get("ano_construcao") or item.get("ano_construcao"),
            "numero_andares": labels.get("numero_andares") or item.get("numero_andares"),
            "elevadores": labels.get("elevadores") or item.get("elevadores"),
            "imagem": images[0] if images else item.get("imagem"),
            "imagens": images,
            "video_url": video_url or item.get("video_url"),
            "mapa_url": map_url or item.get("mapa_url"),
            "bairro": bairro or item.get("bairro"),
            "cidade": cidade or item.get("cidade"),
            "uf": uf or item.get("uf"),
        }
    )
    return enriched, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich grankasa catalog from detail pages.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items (0 = all).")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep in seconds between requests.")
    parser.add_argument("--timeout", type=float, default=12.0, help="Request timeout in seconds.")
    args = parser.parse_args()

    if not INPUT_FILE.exists():
        raise SystemExit(f"Input file not found: {INPUT_FILE}")

    items = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
    )

    enriched_items: list[dict] = []
    errors: dict[str, int] = {}
    started = time.time()

    for idx, item in enumerate(items, start=1):
        enriched, error = enrich_item(session, item, timeout=args.timeout)
        enriched_items.append(enriched)

        if error:
            errors[error] = errors.get(error, 0) + 1

        if args.sleep > 0:
            time.sleep(args.sleep)

        if idx % 10 == 0 or idx == len(items):
            print(f"[{idx}/{len(items)}] processed")

    OUTPUT_FILE.write_text(json.dumps(enriched_items, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "source_file": str(INPUT_FILE),
        "output_file": str(OUTPUT_FILE),
        "total_input": len(items),
        "total_output": len(enriched_items),
        "errors": errors,
        "elapsed_seconds": round(time.time() - started, 2),
        "generated_at_epoch": time.time(),
    }
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
