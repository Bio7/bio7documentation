#!/bin/bash
# Generates the Bio7 API (Javadoc) in the folder api/ (published with GitHub Pages).
#
#   ./make_api.sh <bio7 repository> <Eclipse folder of an installed Bio7>
#   e.g. ./make_api.sh ~/git/bio7 /Applications/Bio7.app/Contents/Eclipse   (macOS)
#        ./make_api.sh ~/git/bio7 /opt/Bio7                                 (Linux, Windows: the Bio7 folder)
#
# The documented classes are listed in api_classes.txt (paths in the bio7
# repository). The plugins of the installed Bio7 are the classpath, its JDK
# runs javadoc. No time stamps, English texts.
set -euo pipefail
cd "$(dirname "$0")"
SRC="${1:?bio7 repository}"
APP="${2:?Eclipse folder of an installed Bio7}"
JAVADOC="$APP/jdk/Contents/Home/bin/javadoc"
[ -x "$JAVADOC" ] || JAVADOC="$APP/jdk/bin/javadoc"
[ -x "$JAVADOC" ] || JAVADOC="javadoc"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# the classpath: the jars and the folders of the plugins; jars with their classes in bin/ are unpacked
CP=""
for p in "$APP"/plugins/*; do
  if [ -d "$p" ]; then
    CP="$CP:$p"; [ -d "$p/bin" ] && CP="$CP:$p/bin"
    for j in "$p"/libs/*.jar "$p"/lib/*.jar "$p"/*.jar; do [ -f "$j" ] && CP="$CP:$j"; done
  elif [[ "$p" == *.jar ]]; then
    CP="$CP:$p"
    unzip -Z1 "$p" > "$TMP/list" 2>/dev/null || true
    if grep -q '^bin/' "$TMP/list"; then
      d="$TMP/$(basename "$p" .jar)"; mkdir -p "$d"; unzip -q -o "$p" 'bin/*' -d "$d" 2>/dev/null || true; CP="$CP:$d/bin"
    fi
  fi
done
FILES=()
while IFS= read -r f; do [ -n "$f" ] && FILES+=("$SRC/$f"); done < api_classes.txt
# the optional api_support.txt: sources of the repository which are not documented but needed for
# the documented classes while the installed Bio7 is older than the repository (e.g., a new class)
mkdir -p "$TMP/src"
if [ -f api_support.txt ]; then
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel="${f#*/src/}"; mkdir -p "$TMP/src/$(dirname "$rel")"; cp "$SRC/$f" "$TMP/src/$rel"
  done < api_support.txt
fi
# into a temporary folder: a failed run keeps the existing api/
"$JAVADOC" -J-Duser.language=en -J-Duser.country=US -locale en_US -d "$TMP/api" -notimestamp -quiet -Xdoclint:none \
  -encoding UTF-8 -docencoding UTF-8 -charset UTF-8 \
  -windowtitle "Bio7 4.0 API" -doctitle "Bio7 4.0 API" -header "Bio7 4.0 API" \
  -bottom "Bio7 4.0 – Eclipse Public License 2.0 – <a href=\"https://bio7.org\">bio7.org</a>" \
  --source-path "$TMP/src" -cp "${CP#:}" "${FILES[@]}"
rm -rf api
mv "$TMP/api" api
echo "Created api/index.html"
