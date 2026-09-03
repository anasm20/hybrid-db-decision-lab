#!/usr/bin/env python3
import json
from pathlib import Path
try:
    import yaml
except ImportError:
    raise SystemExit('Install PyYAML: pip install pyyaml')
ROOT=Path(__file__).resolve().parents[1]
a=yaml.safe_load((ROOT/'cost/assumptions.yaml').read_text())
on=a['onprem']; cl=a['cloud']; hy=a['hybrid']
onprem=(on['server_capex_eur']+on['storage_capex_eur']+on['network_capex_eur'])/on['amortization_months'] + on['electricity_kwh_month']*on['electricity_eur_kwh'] + on['facilities_eur_month']+on['licenses_eur_month']+on['admin_hours_month']*on['admin_hourly_eur']
cloud=sum(cl[k] for k in ['compute_eur_month','database_eur_month','storage_eur_month','network_egress_eur_month','backup_eur_month','support_eur_month']) + cl['admin_hours_month']*cl['admin_hourly_eur']
hybrid=onprem+cloud+hy['shared_tooling_eur_month']+hy['connectivity_eur_month']
out={"provenance":"MODELLED","currency":a['currency'],"monthly":{"onprem":round(onprem,2),"cloud":round(cloud,2),"hybrid":round(hybrid,2)},"source_file":"cost/assumptions.yaml"}
p=ROOT/'site/data/cost.json'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2),encoding='utf-8'); print(p)
