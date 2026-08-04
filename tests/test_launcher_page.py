"""Montagem do HTML final do launcher."""

import json

from warpzone import launcher_page, scheme


def _render(itens):
    return launcher_page.render(scheme.load_scheme(), itens)


def test_nao_sobra_placeholder():
    html = _render([{"nome": "Cockpit", "url": "http://127.0.0.1:5173", "icone": "dashboard"}])
    for marcador in ("__SCHEME__", "__STYLE__", "__APP_JS__", "__BOOKMARKS__"):
        assert marcador not in html


def test_injeta_as_css_vars():
    html = _render([])
    assert "--m3-primary:" in html
    assert "--m3-surface-container-rgb:" in html


def test_injeta_os_bookmarks_como_json_parseavel():
    itens = [{"nome": "Cockpit", "url": "http://127.0.0.1:5173", "icone": "dashboard"}]
    html = _render(itens)
    inicio = html.index('id="bootstrap"')
    abre = html.index(">", inicio) + 1
    fecha = html.index("</script>", abre)
    assert json.loads(html[abre:fecha]) == itens


def test_injeta_o_css_e_o_js():
    html = _render([])
    assert ".omni" in html                   # veio do style.css
    assert "__warpzoneSetBookmarks" in html  # veio do app.js


def test_nome_com_html_nao_vira_marcacao():
    """Nome vem de <title> remoto; tem que entrar como dado, não como tag."""
    html = _render([{"nome": "<img src=x onerror=alert(1)>", "url": "https://x.dev", "icone": "public"}])
    assert "<img src=x onerror=alert(1)>" not in html
