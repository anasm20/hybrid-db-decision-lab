# 12 — Enterprise roadmap

## Stage 1 — Local PostgreSQL PoC

Current repository: prove the methodology and observability path.

## Stage 2 — Real cloud validation

Deploy one secondary site in Azure or another selected provider. Repeat baseline, WAN and switchover/failover scenarios. Capture actual SKU, region and billable resources.

## Stage 3 — Technology matrix

Run equivalent protocols for technologies relevant to the target environment, for example:

- PostgreSQL HA;
- SQL Server Always On / Distributed Availability Groups;
- Oracle Data Guard / RAC where architecturally appropriate.

## Stage 4 — Hybrid management candidates

Evaluate management/control layers separately from database HA:

- Azure Arc / Azure Local;
- Red Hat OpenShift + ACM;
- Nutanix hybrid cloud stack;
- VMware Cloud Foundation;
- database-vendor-specific services.

## Stage 5 — Production controls

Add identity/RBAC, secrets, network segmentation, audit, immutable backup, DR clean room, security monitoring, compliance evidence, real FinOps exports and approved operational runbooks.
