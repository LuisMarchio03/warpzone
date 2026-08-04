"""Converte o que o usuário digita numa URL navegável."""

from __future__ import annotations

import re

# esquema já presente (http://, https://, file://, ...)
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0"})


def normalize(raw: str) -> str | None:
    """Devolve a URL a navegar, ou None quando a entrada não é um endereço.

    Não há busca web: este é um browser de destinos internos, então tudo que
    não se parece com endereço é rejeitado em vez de virar consulta.
    """
    text = raw.strip()
    if not text or any(char.isspace() for char in text):
        return None

    if _SCHEME_RE.match(text):
        return text

    # host = tudo antes da primeira barra, interrogação ou cerquilha
    host = re.split(r"[/?#]", text, maxsplit=1)[0]
    hostname = host.split(":", 1)[0]

    if hostname in _LOCAL_HOSTS:
        return f"http://{text}"

    if "." in hostname and not hostname.startswith(".") and not hostname.endswith("."):
        return f"https://{text}"

    return None
