"""Normalização do que o usuário digita no launcher."""

import pytest

from warpzone.urls import normalize


@pytest.mark.parametrize(
    "raw, esperado",
    [
        # já tem esquema: passa direto
        ("http://127.0.0.1:5173", "http://127.0.0.1:5173"),
        ("https://grafana.exemplo.dev/d/abc", "https://grafana.exemplo.dev/d/abc"),
        ("file:///tmp/x.html", "file:///tmp/x.html"),
        # host local: http
        ("localhost:5173", "http://localhost:5173"),
        ("127.0.0.1:8765/docs", "http://127.0.0.1:8765/docs"),
        ("localhost", "http://localhost"),
        ("0.0.0.0:3000", "http://0.0.0.0:3000"),
        # domínio: https
        ("grafana.exemplo.dev", "https://grafana.exemplo.dev"),
        ("wiki.exemplo.com/doc/abc", "https://wiki.exemplo.com/doc/abc"),
        ("jira.exemplo.com.br:8443/browse/PM-1", "https://jira.exemplo.com.br:8443/browse/PM-1"),
        # espaço em volta é aparado
        ("  localhost:5173  ", "http://localhost:5173"),
    ],
)
def test_normaliza_entradas_validas(raw, esperado):
    assert normalize(raw) == esperado


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "cockpit",             # palavra solta não é URL
        "abrir o grafana",     # frase com espaço
        "pm 18090",
        ".",
        ".com",
        "grafana.",
    ],
)
def test_rejeita_entradas_que_nao_sao_url(raw):
    assert normalize(raw) is None
