"""Argumentos de linha de comando."""

import pytest

from warpzone.cli import destino


@pytest.mark.parametrize(
    "argv, esperado",
    [
        ([], None),
        (["https://google.com"], "https://google.com"),
        (["--url", "https://google.com"], "https://google.com"),
        (["--url=localhost:5173"], "http://localhost:5173"),
        (["--url", "grafana.exemplo.dev"], "https://grafana.exemplo.dev"),
        (["localhost:5173"], "http://localhost:5173"),
    ],
)
def test_destino(argv, esperado):
    assert destino(argv) == esperado


@pytest.mark.parametrize(
    "argv",
    [
        ["--url"],                                 # flag sem valor
        ["--url", "cockpit"],                      # não é endereço
        ["cockpit"],
        ["a.com", "--url", "b.com"],               # URL duas vezes
        ["--nao-existe"],
    ],
)
def test_destino_invalido_encerra_com_codigo_2(argv, capsys):
    with pytest.raises(SystemExit) as erro:
        destino(argv)
    assert erro.value.code == 2
    assert capsys.readouterr().err
