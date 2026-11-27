#!/bin/zsh
# render.sh <archivo.svg|html> <salida.png> <ancho> [alto]
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
in="$1"; out="$2"; w="$3"; h="${4:-$3}"
case "$in" in
  *.svg) tmp="$(mktemp -t sello).html"
         print -r -- "<!doctype html><html><body style=\"margin:0;background:transparent\"><img src=\"file://$PWD/$in\" style=\"display:block;width:${w}px;height:${h}px\"></body></html>" > "$tmp"; src="$tmp";;
  *) src="$PWD/$in";;
esac
"$CH" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --default-background-color=00000000 --window-size="$w,$h" --screenshot="$PWD/$out" "file://$src" >/dev/null 2>&1
