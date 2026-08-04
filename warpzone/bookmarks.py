"""Atalhos fixos do launcher, persistidos em ~/.config/warpzone."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config/warpzone/bookmarks.json"

ICONE_PADRAO = "public"

# Vazio de propósito: quem escolhe os favoritos é o usuário, pelo card "+"
# do launcher ou pelo Ctrl+D. O app não chega opinando destino de ninguém.
SEED: list[dict] = []


def load(path: Path | None = None) -> list[dict]:
    """Lê os atalhos. Primeira execução grava o seed; arquivo quebrado vira .bak."""
    destino = path or CONFIG_PATH
    if not destino.exists():
        save(list(SEED), destino)
        return list(SEED)

    try:
        dados = json.loads(destino.read_text(encoding="utf-8"))
        if not isinstance(dados, list):
            raise ValueError("esperava uma lista")
    except Exception:
        destino.with_name(destino.name + ".bak").write_bytes(destino.read_bytes())
        save(list(SEED), destino)
        return list(SEED)

    return [_normalizar(item) for item in dados if _valido(item)]


def save(itens: list[dict], path: Path | None = None) -> None:
    destino = path or CONFIG_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(itens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def add(
    nome: str,
    url: str,
    path: Path | None = None,
    icone: str = "bookmark",
) -> list[dict]:
    """Anexa um atalho. URL repetida é ignorada; devolve a lista final."""
    itens = load(path)
    if not url:
        return itens
    if any(_chave(item["url"]) == _chave(url) for item in itens):
        return itens
    itens.append({"nome": nome or url, "url": url, "icone": icone})
    save(itens, path)
    return itens


def update(
    url_original: str,
    nome: str,
    url: str,
    icone: str,
    path: Path | None = None,
) -> list[dict]:
    """Reescreve o atalho identificado por url_original, no mesmo lugar da lista.

    URL que não existe na lista não vira atalho novo: editar é editar. Quem
    cria é o add().
    """
    itens = load(path)
    alvo = _chave(url_original)
    for posicao, item in enumerate(itens):
        if _chave(item["url"]) == alvo:
            itens[posicao] = {
                "nome": nome or url,
                "url": url,
                "icone": icone or ICONE_PADRAO,
            }
            save(itens, path)
            break
    return itens


def remove(url: str, path: Path | None = None) -> list[dict]:
    itens = [item for item in load(path) if _chave(item["url"]) != _chave(url)]
    save(itens, path)
    return itens


def _chave(url: str) -> str:
    """Identidade do atalho. O Ctrl+D traz a URL com barra final que o
    usuário nunca digitou, e os dois são o mesmo destino."""
    return url.rstrip("/")


def _valido(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("nome"), str)
        and isinstance(item.get("url"), str)
        and bool(item["url"])
    )


def _normalizar(item: dict) -> dict:
    return {
        "nome": item["nome"],
        "url": item["url"],
        "icone": item.get("icone") or ICONE_PADRAO,
    }
