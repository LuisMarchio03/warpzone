"""Entrada do warpzone: `python3 -m warpzone [URL]`."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk  # noqa: E402

from . import urls  # noqa: E402
from .app import APP_ID, CockpitWindow  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    destino = urls.normalize(argumentos[0]) if argumentos else None

    # define o app_id que o Hyprland enxerga como "class"
    GLib.set_prgname(APP_ID)

    janela = CockpitWindow(destino)
    janela.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
