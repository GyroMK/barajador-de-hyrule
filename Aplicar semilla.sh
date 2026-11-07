#!/bin/sh
# Aplica una semilla del Barajador de Hyrule. Arrastra aquí el archivo semilla .json o pega el código cuando lo pida.
cd "$(dirname "$0")" || exit 1
exec python3 programa/barajador.py "$@"
