"""Costura o HTML final do launcher com CSS, JS e dados já embutidos."""

from __future__ import annotations

import html as html_mod
import json
from pathlib import Path

from . import scheme

LAUNCHER_DIR = Path(__file__).parent / "launcher"


def render(dados_scheme: dict, itens: list[dict], base: Path = LAUNCHER_DIR) -> str:
    """HTML do launcher pronto para load_html, sem nenhum recurso externo."""
    html = (base / "index.html").read_text(encoding="utf-8")
    return (
        html.replace("/*__SCHEME__*/", scheme.css_block(dados_scheme))
        .replace("/*__STYLE__*/", (base / "style.css").read_text(encoding="utf-8"))
        .replace("/*__APP_JS__*/", (base / "app.js").read_text(encoding="utf-8"))
        .replace("/*__BOOKMARKS__*/", _json_seguro(itens))
    )


def render_error(
    dados_scheme: dict,
    uri: str,
    dica: str | None,
    base: Path = LAUNCHER_DIR,
) -> str:
    """Página de falha. A URI é escapada: vem de fonte não confiável."""
    pagina = (base / "error.html").read_text(encoding="utf-8")
    bloco_dica = ""
    if dica:
        bloco_dica = (
            '<div class="falha__dica"><p>o serviço parece estar parado — suba com:</p>'
            f"<code>{html_mod.escape(dica)}</code></div>"
        )
    # a ordem importa: __DICA__ entra antes de __URI__ para que a URI já
    # escapada não seja reprocessada
    return (
        pagina.replace("/*__SCHEME__*/", scheme.css_block(dados_scheme))
        .replace("/*__STYLE__*/", (base / "style.css").read_text(encoding="utf-8"))
        .replace("__DICA__", bloco_dica)
        .replace("__URI__", html_mod.escape(uri, quote=True))
    )


def _json_seguro(itens: list[dict]) -> str:
    """JSON que não consegue fechar a tag <script> que o contém.

    O nome do atalho pode vir do <title> de uma página remota (Ctrl+D), e
    json.dumps não escapa `<` por padrão — um título com `</script>` sairia
    da tag e viraria marcação.
    """
    return (
        json.dumps(itens, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
