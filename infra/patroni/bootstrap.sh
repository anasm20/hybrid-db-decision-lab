#!/usr/bin/env bash
set -euo pipefail

mkdir -p "${PATRONI_POSTGRESQL_DATA_DIR:-/var/lib/postgresql/data}"
chmod 0700 "${PATRONI_POSTGRESQL_DATA_DIR:-/var/lib/postgresql/data}"
python3 - <<'PY2'
import os
from pathlib import Path
t=Path('/etc/patroni.yml').read_text()
Path('/tmp/patroni.yml').write_text(os.path.expandvars(t))
PY2
exec patroni /tmp/patroni.yml
