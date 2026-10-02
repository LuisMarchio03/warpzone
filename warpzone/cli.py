"""Argumentos de linha de comando, separados do GTK para serem testáveis."""

from __future__ import annotations

import argparse

from . import urls


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warpzone",
        description="Abre uma URL como aplicativo desktop. Sem URL, abre o launcher.",
    )
    parser.add_argument("posicional", nargs="?", metavar="URL", help="endereço a abrir")
    parser.add_argument("--url", dest="url", metavar="URL", help="endereço a abrir")
    return parser


def destino(argv: list[str]) -> str | None:
    """Devolve a URL normalizada a abrir, ou None para abrir o launcher.

    Encerra com código 2 (padrão do argparse) quando a URL vem duas vezes ou
    não tem forma de endereço: vinda do terminal, falhar é melhor que cair
    no launcher sem explicação.
    """
    parser = _parser()
    args = parser.parse_args(argv)

    if args.posicional and args.url:
        parser.error("informe a URL só uma vez: posicional ou --url")

    bruto = args.url or args.posicional
    if bruto is None:
        return None

    url = urls.normalize(bruto)
    if url is None:
        parser.error(f"não parece um endereço: {bruto!r}")
    return url
