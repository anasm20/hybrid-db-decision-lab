# 01 — Research question

## Main question

**Which operating architecture — On-Premises, Cloud-only or Hybrid — best satisfies a defined database workload under explicit performance, resilience, data-integrity, portability and cost requirements?**

The PoC deliberately does not start with a preferred vendor or architecture. A candidate can only be recommended after it passes mandatory gates and is evaluated under the same protocol.

## Candidate modes

- **ON_PREM_ONLY** — primary database and application are local.
- **CLOUD_ONLY** — primary database and application are hosted in the selected cloud.
- **HYBRID** — one site is primary and the other is a standby/secondary site; planned switchover can exchange roles.

## Hypotheses

- H0: No operational mode has a practically meaningful advantage under the defined requirements.
- H1: At least one mode has a practically meaningful advantage for one or more scenarios.
- H2: The preferred mode is workload-dependent; no single architecture is globally optimal.

H2 is the architecture hypothesis this lab is designed to test, not to assume.
