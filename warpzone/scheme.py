"""Lê o esquema de cores dinâmico do Caelestia e o traduz para CSS."""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEME_PATH = Path.home() / ".local/state/caelestia/scheme.json"

# Usado quando o Caelestia não está instalado ou o arquivo está ilegível.
# Snapshot do esquema escuro em uso quando o app foi escrito.
FALLBACK: dict[str, str] = {
    "background": "0e0e12",
    "onBackground": "e7e4f0",
    "surface": "0e0e12",
    "surfaceContainerLow": "131318",
    "surfaceContainer": "191920",
    "surfaceContainerHigh": "1f1f26",
    "surfaceContainerHighest": "25252e",
    "onSurface": "e7e4f0",
    "onSurfaceVariant": "acaab5",
    "outline": "76747f",
    "outlineVariant": "484750",
    "primary": "c3c3ee",
    "primaryDim": "b5b5e0",
    "onPrimary": "3c3d61",
    "primaryContainer": "4e4f74",
    "onPrimaryContainer": "e2e0ff",
    "secondary": "c6c4dd",
    "tertiary": "ffe2ff",
    "error": "ffb4ab",
    "onError": "690005",
    "errorContainer": "93000a",
    "onErrorContainer": "ffdad6",
    "shadow": "000000",
}

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def load_scheme(path: Path | None = None) -> dict:
    """Devolve {"mode": "dark"|"light", "colours": {...}}. Nunca levanta."""
    origem = path or SCHEME_PATH
    try:
        bruto = json.loads(origem.read_text(encoding="utf-8"))
        cores = bruto["colours"]
        if not isinstance(cores, dict) or not cores:
            raise ValueError("colours vazio ou não é objeto")
        modo = bruto.get("mode", "dark")
    except Exception:  # arquivo ausente, JSON quebrado, chave faltando
        cores, modo = FALLBACK, "dark"

    return {
        "mode": "light" if modo == "light" else "dark",
        "colours": {
            nome: _com_cerquilha(valor)
            for nome, valor in cores.items()
            if isinstance(valor, str)
        },
    }


def to_css_var(nome: str) -> str:
    """surfaceContainerHigh -> --m3-surface-container-high"""
    kebab = _CAMEL_BOUNDARY.sub("-", nome).lower().replace("_", "-")
    return f"--m3-{kebab}"


def css_block(dados: dict) -> str:
    """Bloco :root com cada cor em hex e, quando possível, em triplet RGB.

    O triplet existe para o CSS poder fazer rgba(var(--x-rgb), .55) sem
    depender de color-mix().
    """
    linhas = [f"  color-scheme: {dados['mode']};"]
    for nome, valor in sorted(dados["colours"].items()):
        var = to_css_var(nome)
        linhas.append(f"  {var}: {valor};")
        triplet = _triplet(valor)
        if triplet:
            linhas.append(f"  {var}-rgb: {triplet};")
    return ":root {\n" + "\n".join(linhas) + "\n}\n"


def _com_cerquilha(valor: str) -> str:
    return valor if valor.startswith("#") else f"#{valor}"


def _triplet(valor: str) -> str | None:
    corpo = valor.lstrip("#")
    if len(corpo) != 6:
        return None
    try:
        r, g, b = (int(corpo[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    return f"{r}, {g}, {b}"
