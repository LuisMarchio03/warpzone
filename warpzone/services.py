"""Descobre se a falha de carregamento é só o serviço do cockpit parado."""

from __future__ import annotations

import subprocess
from urllib.parse import urlsplit

# porta -> unit systemd do usuário
UNIDADES: dict[int, str] = {
    5173: "claude-cockpit-frontend.service",
    8765: "claude-cockpit-backend.service",
}

_HOSTS_LOCAIS = frozenset({"127.0.0.1", "localhost", "0.0.0.0"})


def systemctl_state(unidade: str) -> str:
    """Estado da unit ('active', 'inactive', 'failed', ...)."""
    resultado = subprocess.run(
        ["systemctl", "--user", "is-active", unidade],
        capture_output=True,
        text=True,
        timeout=3,
    )
    return resultado.stdout.strip()


def hint_for(uri: str, runner=systemctl_state) -> str | None:
    """Comando a sugerir, ou None quando não há dica útil."""
    try:
        partes = urlsplit(uri)
        if partes.hostname not in _HOSTS_LOCAIS:
            return None
        unidade = UNIDADES.get(partes.port or 0)
    except ValueError:  # porta não numérica
        return None
    if unidade is None:
        return None

    try:
        estado = runner(unidade)
    except Exception:  # systemctl ausente, timeout, permissão
        return None

    if estado == "active":
        return None
    return f"systemctl --user start {unidade}"
