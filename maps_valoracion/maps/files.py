"""Lectura de archivos subidos: PDF, Excel, CSV/TXT/MD/JSON e imágenes."""
from __future__ import annotations

import base64
import io

import pandas as pd
from pypdf import PdfReader

from .engine import Ctx, MapsError, call_stream

IMG_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
TRANSCRIBE = ("Transcribe fielmente todo el texto y todas las tablas (especialmente las financieras) de este documento a markdown. "
              "No resumas ni inventes: si algo no se lee, escribe [ilegible].")


def read_upload(name: str, data: bytes, ctx: Ctx | None) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in ("txt", "md", "csv", "tsv", "json"):
        return data.decode("utf-8", errors="replace")
    if ext in ("xlsx", "xlsm", "xls", "ods"):
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None)
        return "\n\n".join(f"--- hoja: {sn} ---\n" + df.dropna(how="all").to_csv(index=False, header=False)
                           for sn, df in sheets.items())
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [pg.extract_text() or "" for pg in reader.pages]
        if len("".join("".join(pages).split())) >= 100 * len(pages):
            return "\n".join(f"--- página {i + 1} ---\n{t}" for i, t in enumerate(pages))
        # PDF escaneado: que lo lea Claude directamente.
        if not ctx:
            raise MapsError("El PDF no tiene texto seleccionable y no hay API key para leerlo con Claude.")
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                "data": base64.standard_b64encode(data).decode()}}
        return call_stream(ctx.client, ctx.settings, system="Eres un transcriptor preciso.",
                           content=[block, {"type": "text", "text": TRANSCRIBE}]).text
    if ext in IMG_TYPES:
        if not ctx:
            raise MapsError("Para leer imágenes hace falta la API key.")
        block = {"type": "image", "source": {"type": "base64", "media_type": IMG_TYPES[ext],
                                             "data": base64.standard_b64encode(data).decode()}}
        return call_stream(ctx.client, ctx.settings, system="Eres un transcriptor preciso.",
                           content=[block, {"type": "text", "text": TRANSCRIBE}]).text
    raise MapsError(f"Formato no soportado: {name}. Usa PDF, Excel, CSV, TXT, MD, JSON o imagen.")
