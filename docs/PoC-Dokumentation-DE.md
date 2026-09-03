# PoC-Dokumentation — Hybrid Database Decision Lab

## 1. Ziel

Dieses Proof of Concept stellt eine reproduzierbare Methode bereit, um Datenbankarchitekturen **vor** einer Technologieentscheidung zu vergleichen. Bewertet werden On-Premises-, Cloud-only- und Hybrid-Betrieb anhand identischer Workloads, definierter Fehlerfälle, messbarer SLOs und eines getrennten Kostenmodells.

Die Kernfrage lautet nicht „Welche Plattform ist allgemein die beste?“, sondern:

> Welche Architektur erfüllt für einen definierten Workload und definierte nichtfunktionale Anforderungen die verbindlichen Gates und liefert anschließend den robustesten Trade-off aus Performance, Resilienz, Datenintegrität, Kosten, Souveränität, Portabilität und Betriebsaufwand?

## 2. Scope

Der erste technische PoC nutzt PostgreSQL 16, Patroni, HAProxy, eine synthetische Demo-Service-API, k6, pgbench, Prometheus, Loki und Grafana. Die lokale Umgebung simuliert zwei Standorte. Ein optionales Terraform-Modul stellt eine kleine Azure-VM für einen späteren echten Cloud-Validierungslauf bereit.

Nicht im Scope der ersten Version sind Produktions-Security-Hardening, echte kommunale Daten, vollständige Multi-Region-DR-Topologien sowie SQL Server-/Oracle-Vergleichsmessungen.

## 3. Architektur

```text
k6 / pgbench
    |
Demo API
    |
HAProxy (Primary routing)
    |
+--------------------------+
|                          |
PostgreSQL 1            PostgreSQL 2
Patroni                  Patroni
|                          |
+----------- etcd ----------+

Demo API -> Prometheus metrics ----+
DB metrics exporter -> Prometheus -----+--> Grafana
Demo API logs -> Loki --------------+

Failure runner -> raw evidence -> Python analysis -> GitHub Pages
Cost assumptions ---------------------> Python cost model -> GitHub Pages
```

## 4. Betriebsmodi

### ON_PREM_ONLY

Lokaler Standort ist aktiv. Cloud ist nicht für den laufenden Dienst erforderlich.

### CLOUD_ONLY

Cloud-Standort ist aktiv. Lokaler Standort ist nicht für den laufenden Dienst erforderlich.

### HYBRID

Ein Standort führt als Primary, der andere hält eine replizierte Standby-Datenbank. Ein geplanter Switchover oder ungeplanter Failover verändert die aktive Rolle.

## 5. Wissenschaftliche Kontrollen

### Präregistrierung

Vor jedem Experiment wird `protocol.yaml` erzeugt. Dort stehen Hypothese, Primärmetrik, Workload, Failure Injection und Akzeptanzkriterien. Die Datei kann vor dem Lauf committed werden.

### Kontrollierte Variablen

Für Kandidatenvergleiche müssen mindestens Workload, Testdauer, Datenmenge, Client, Datenbankversion bzw. funktional äquivalenter Stack sowie Ressourcen-/Kosten-Normalisierung dokumentiert sein.

### Wiederholungen

Ein einzelner Lauf darf nicht als Architekturbeweis interpretiert werden. Für die erste Demonstration sind zehn Läufe vorgesehen. Ergebnisberichte verwenden Verteilungen und Konfidenzintervalle.

### Provenienz

- `MEASURED`: aus einem tatsächlich ausgeführten Testlauf.
- `SIMULATED`: aus einer Emulation, z. B. künstliche WAN-Latenz.
- `MODELLED`: aus Annahmen, z. B. TCO.
- `ASSESSED`: Experten-/Stakeholder-Bewertung, z. B. Souveränität.

Diese Kategorien dürfen nicht vermischt werden.

## 6. Messgrößen

### Application

- Requests/s
- p50/p95/p99
- HTTP 5xx rate
- erfolgreiche Writes

### Database

- Primary/Replica-Rolle
- Replication Lag
- Connections
- committed transactions
- DB-Erreichbarkeit

### Resilience

- Failure detection
- Promotion time
- Write recovery
- RTO
- acknowledged-write loss als praktischer RPO-Indikator

### Cost

- monatliche effektive Kosten
- 3-/5-Jahres-TCO
- Kosten pro 1 Mio. erfolgreiche Requests/Transaktionen

## 7. Failure-Experiment

1. HA-Cluster läuft stabil.
2. k6 erzeugt steady load.
3. Ein separater Probe-Writer schreibt fortlaufend nummerierte bestätigte Datensätze.
4. Der Runner erkennt den aktuellen Primary.
5. Nach Warm-up wird der Primary-Container gestoppt.
6. Patroni promotet einen geeigneten Replica-Knoten.
7. HAProxy routet neue DB-Verbindungen zum neuen Primary.
8. Der Runner wartet auf einen erfolgreichen Write über die API.
9. `RTO = Zeitpunkt erster erfolgreicher Write - Failure Injection`.
10. Die höchste vor Ausfall bestätigte Probe wird mit der höchsten nach Recovery vorhandenen Probe verglichen.
11. Events, Ergebnis, k6-Output und SHA-256-Prüfsummen werden im Experimentordner abgelegt.

## 8. Grafana

Das Dashboard wird beim Start automatisch provisioniert und enthält:

- API Requests/s
- API p95
- API Error Rate
- DB Primary State
- Replication Lag
- DB Connections
- DB Node Availability
- Commit Counter
- Exporter Errors
- Loki Application Logs

Grafana ist die **operative Sicht**. Die GitHub-Pages-App ist die **Entscheidungssicht**.

## 9. Kostenmodell

`cost/assumptions.yaml` enthält nur Beispielwerte und ist daher `MODELLED`. Für einen formalen Vergleich müssen die Zahlen durch dokumentierte Quellen ersetzt werden, z. B. Cloud Billing Export/Invoice, offizielle Preis-API oder interne On-Prem-Kostenallokation.

Hybridkosten dürfen nicht künstlich klein gerechnet werden: Reservekapazität, Connectivity und doppelter Betriebsaufwand müssen berücksichtigt werden.

## 10. Entscheidungslogik

Zuerst gelten Mandatory Gates. Beispiel:

- RTO < 30 s
- kein Verlust bestätigter Writes
- Restore erfolgreich
- vereinbarte Security-/Residency-Anforderung erfüllt

Erst danach wird gewichtet. Gewichte sind Annahmen und werden in einer Sensitivitätsanalyse variiert. Ein „Gewinner“ wird im Repository absichtlich nicht aus Platzhalterdaten berechnet.

## 11. Reale Cloud-Validierung

Die lokale Zwei-Site-Umgebung ist eine Simulation. Für eine belastbare Hybrid-Aussage wird anschließend ein repräsentativer Teil gegen eine echte Cloud-Site wiederholt:

- Baseline
- WAN-Latenz/Replication
- geplanter Switchover oder Failure

Dabei werden Region, SKU, Storage, Netzwerkpfad und tatsächliche Kostenquelle im Experiment-Metadata festgehalten.

## 12. Erweiterung für weitere relevante Technologien

Nach dem PostgreSQL-PoC kann dasselbe Protokoll auf weitere Kandidaten übertragen werden:

- SQL Server Always On / Distributed Availability Groups
- Oracle Data Guard und, sofern sinnvoll, Oracle RAC
- Managed PostgreSQL/SQL-Dienste
- Azure Arc/Azure Local, OpenShift/ACM, Nutanix oder andere Management-Layer

Wichtig ist, Management-Plattform und Datenbank-HA getrennt zu bewerten.

## 13. Schlussaussage

Das Ergebnis des PoC ist kein universeller Produkt-Rang. Das Ergebnis ist ein **nachvollziehbarer Entscheidungsprozess**, bei dem jede Empfehlung auf Anforderungen, Protokoll, Rohdaten, Messmethodik, Kostenannahmen und Limitationen zurückverfolgt werden kann.
