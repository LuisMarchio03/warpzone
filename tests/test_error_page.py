"""Página de falha de carregamento."""

from warpzone import launcher_page, scheme


def _render(uri, dica=None):
    return launcher_page.render_error(scheme.load_scheme(), uri, dica)


def test_nao_sobra_placeholder():
    html = _render("http://127.0.0.1:5173/")
    for marcador in ("__SCHEME__", "__STYLE__", "__URI__", "__DICA__"):
        assert marcador not in html


def test_mostra_a_uri():
    assert "http://127.0.0.1:5173/" in _render("http://127.0.0.1:5173/")


def test_sem_dica_nao_desenha_o_bloco():
    # a classe também aparece no CSS embutido; o que não pode existir é a div
    assert '<div class="falha__dica">' not in _render("https://x.dev")


def test_com_dica_desenha_o_comando():
    html = _render(
        "http://127.0.0.1:5173/", "systemctl --user start claude-cockpit-frontend.service"
    )
    assert '<div class="falha__dica">' in html
    assert "systemctl --user start claude-cockpit-frontend.service" in html


def test_uri_hostil_e_escapada():
    html = _render('https://x.dev/"><script>alert(1)</script>')
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
