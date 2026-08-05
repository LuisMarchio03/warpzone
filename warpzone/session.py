"""Persistência da sessão web: cookies gravados em disco entre aberturas.

O `base-data-directory` do WebsiteDataManager cobre localStorage, IndexedDB e
cache, mas não cobre cookies: no WebKitGTK o cookie é memória-only até alguém
chamar set_persistent_storage(). Sem esta chamada o usuário desloga de todo
site a cada abertura.
"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("WebKit2", "4.1")

from gi.repository import WebKit2  # noqa: E402

COOKIE_FILE = "cookies.sqlite"


def cookie_path(data_dir: Path) -> Path:
    """Onde o banco de cookies mora dentro do diretório de dados."""
    return data_dir / COOKIE_FILE


def enable_persistence(gerenciador, data_dir: Path) -> Path:
    """Liga a gravação de cookies em disco; devolve o caminho usado.

    Recebe o WebsiteDataManager pronto em vez de construí-lo, para que o teste
    passe um dublê e a suíte não dependa de GTK.

    O WebKit não devolve status nem levanta exceção se o caminho for inválido,
    então o diretório é criado aqui antes da chamada.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    caminho = cookie_path(data_dir)
    gerenciador.get_cookie_manager().set_persistent_storage(
        str(caminho), WebKit2.CookiePersistentStorage.SQLITE
    )
    return caminho
