#!/bin/sh
set -eu
kit_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$kit_root/install_skill.py" install "$@"
