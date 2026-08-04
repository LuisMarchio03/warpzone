"""Dica de systemctl quando um host local do cockpit não responde."""

from warpzone import services


def _parado(_unidade):
    return "inactive"


def _ativo(_unidade):
    return "active"


def _explode(_unidade):
    raise OSError("systemctl sumiu")


def test_frontend_parado_sugere_o_start():
    dica = services.hint_for("http://127.0.0.1:5173/", runner=_parado)
    assert dica == "systemctl --user start claude-cockpit-frontend.service"


def test_backend_parado_sugere_o_start():
    dica = services.hint_for("http://localhost:8765/docs", runner=_parado)
    assert dica == "systemctl --user start claude-cockpit-backend.service"


def test_servico_ativo_nao_gera_dica():
    assert services.hint_for("http://127.0.0.1:5173/", runner=_ativo) is None


def test_porta_desconhecida_nao_gera_dica():
    assert services.hint_for("http://127.0.0.1:9999/", runner=_parado) is None


def test_host_remoto_nao_gera_dica():
    assert services.hint_for("https://grafana.exemplo.dev", runner=_parado) is None


def test_uri_lixo_nao_quebra():
    assert services.hint_for("", runner=_parado) is None
    assert services.hint_for("nao://é//uri", runner=_parado) is None


def test_falha_do_systemctl_e_engolida():
    assert services.hint_for("http://127.0.0.1:5173/", runner=_explode) is None
