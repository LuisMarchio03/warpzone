"""Persistência de cookies: a chamada que faltava no WebsiteDataManager."""

import gi

gi.require_version("WebKit2", "4.1")

from gi.repository import WebKit2  # noqa: E402

from warpzone import session  # noqa: E402


class _CookieManagerFalso:
    """Registra o que o WebKit receberia, sem subir WebKit nenhum."""

    def __init__(self):
        self.chamadas = []

    def set_persistent_storage(self, caminho, formato):
        self.chamadas.append((caminho, formato))


class _GerenciadorFalso:
    def __init__(self):
        self.cookie_manager = _CookieManagerFalso()

    def get_cookie_manager(self):
        return self.cookie_manager


def test_cookie_path_fica_no_diretorio_de_dados(tmp_path):
    assert session.cookie_path(tmp_path) == tmp_path / "cookies.sqlite"


def test_cria_o_diretorio_de_dados_ausente(tmp_path):
    destino = tmp_path / "nao" / "existe"
    session.enable_persistence(_GerenciadorFalso(), destino)
    assert destino.is_dir()


def test_liga_a_gravacao_em_sqlite_no_caminho_certo(tmp_path):
    """Sem esta chamada o cookie é memória-only e o login morre ao fechar."""
    gerenciador = _GerenciadorFalso()
    caminho = session.enable_persistence(gerenciador, tmp_path)
    assert gerenciador.cookie_manager.chamadas == [
        (str(tmp_path / "cookies.sqlite"), WebKit2.CookiePersistentStorage.SQLITE)
    ]
    assert caminho == tmp_path / "cookies.sqlite"
