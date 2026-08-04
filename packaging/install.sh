#!/usr/bin/env sh
# Instala o Warpzone no ~/.local — sem sudo, sem tocar em nada fora da home.
#
#   sh packaging/install.sh              instala e abre uma vez pra você conferir
#   sh packaging/install.sh --no-abrir   só instala
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONES="$HOME/.local/share/icons/hicolor/scalable/apps"

ABRIR=1
[ "${1:-}" = "--no-abrir" ] && ABRIR=0

# --- pré-requisitos: tudo vem do sistema, nada de pip ------------------------
FALTANDO=""
/usr/bin/python3 -c "import gi" 2>/dev/null || FALTANDO="$FALTANDO python-gobject"
/usr/bin/python3 - <<'PY' 2>/dev/null || FALTANDO="$FALTANDO webkit2gtk-4.1"
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2  # noqa: F401
PY

if [ -n "$FALTANDO" ]; then
  echo "faltam dependências do sistema:$FALTANDO" >&2
  echo "no Arch/CachyOS:  sudo pacman -S --needed$FALTANDO" >&2
  exit 1
fi

# --- instalação --------------------------------------------------------------
mkdir -p "$BIN" "$APPS" "$ICONES"

cat > "$BIN/warpzone" <<EOF
#!/usr/bin/env sh
# gerado por packaging/install.sh — aponta para o repo, não copia o código
export PYTHONPATH="$RAIZ\${PYTHONPATH:+:\$PYTHONPATH}"
exec /usr/bin/python3 -m warpzone "\$@"
EOF
chmod +x "$BIN/warpzone"

cp "$RAIZ/packaging/warpzone.svg" "$ICONES/warpzone.svg"
cp "$RAIZ/packaging/warpzone.desktop" "$APPS/warpzone.desktop"

update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# --- relatório ---------------------------------------------------------------
echo "Warpzone instalado."
echo
echo "  sem terminal : procure \"Warpzone\" no launcher de aplicativos"
echo "  no terminal  : warpzone [URL]"
echo
echo "  binário  $BIN/warpzone"
echo "  atalho   $APPS/warpzone.desktop"
echo "  código   $RAIZ"

if ! printf '%s\n' "$PATH" | tr ':' '\n' | grep -qx "$BIN"; then
  echo
  echo "AVISO: $BIN não está no PATH — o atalho do menu funciona mesmo assim,"
  echo "       mas o comando \`warpzone\` no terminal não vai resolver."
fi

if [ "$ABRIR" = "1" ]; then
  echo
  echo "abrindo uma vez pra conferir…"
  setsid "$BIN/warpzone" >/dev/null 2>&1 &
fi
