#!/usr/bin/env python3
import json, py_compile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for p in ROOT.rglob('*.py'):
    try: py_compile.compile(str(p),doraise=True)
    except Exception as e: errors.append(f'{p}: {e}')
for p in ROOT.rglob('*.json'):
    try: json.loads(p.read_text())
    except Exception as e: errors.append(f'{p}: {e}')
if errors:
    print('\n'.join(errors)); raise SystemExit(1)
print('Repository validation OK')
