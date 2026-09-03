#!/usr/bin/env python3
import json
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
weights=yaml.safe_load((ROOT/'cost/decision_weights.yaml').read_text())
cost=json.loads((ROOT/'site/data/cost.json').read_text()) if (ROOT/'site/data/cost.json').exists() else {"monthly":{}}
# This file is intentionally conservative: only assessed dimensions are scored until
# per-candidate measured experiment datasets exist.
out={
  "provenance":"ASSESSED_AND_MODELLED",
  "status":"FRAMEWORK_ONLY",
  "message":"A comparative winner is intentionally not calculated until measured datasets exist for all candidates under the same protocol.",
  "weights":weights['weights'],
  "assessed_scores":weights['assessed_scores_0_to_100'],
  "monthly_cost":cost.get('monthly',{}),
  "mandatory_gates":weights['mandatory_gates']
}
p=ROOT/'site/data/decision.json'; p.write_text(json.dumps(out,indent=2)); print(p)
