#!/usr/bin/env sh
# Desinstala o Warpzone. Por padrão preserva seus dados.
#
#   sh packaging/uninstall.sh          remove o app, mantém favoritos e cookies
#   sh packaging/uninstall.sh --tudo   remove também ~/.config/warpzone e ~/.local/share/warpzone
set -eu

BIN="$HOME/.local/bin/warpzone"
APP="$HOME/.local/share/applications/warpzone.desktop"
ICONE="$HOME/.local/share/icons/hicolor/scalable/apps/warpzone.svg"
CONFIG="$HOME/.config/warpzone"
DADOS="$HOME/.local/share/warpzone"

rm -f "$BIN" "$APP" "$ICONE"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo "removidos: binário, atalho de menu e ícone."

if [ "${1:-}" = "--tudo" ]; then
  rm -rf "$CONFIG" "$DADOS"
  echo "removidos também: favoritos ($CONFIG) e cookies ($DADOS)."
else
  echo
  echo "preservados (use --tudo para apagar):"
  [ -e "$CONFIG" ] && echo "  favoritos  $CONFIG"
  [ -e "$DADOS" ]  && echo "  cookies    $DADOS"
fi

echo
echo "o código em si não foi tocado — apague a pasta do repo se quiser."
