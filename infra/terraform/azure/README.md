# Optional Azure validation site

This Terraform is intentionally small: it creates one Linux VM and network resources for a **real-cloud validation run**. It does not claim to be a production HA design.

Before apply:

```bash
az login
terraform init
terraform plan -var='ssh_public_key=ssh-ed25519 AAAA...'
terraform apply -var='ssh_public_key=ssh-ed25519 AAAA...'
```

Record the Azure region, VM SKU, disk type, deployment timestamp and actual billed/estimated cost in the experiment metadata. Restrict the NSG source range before exposing anything beyond a disposable PoC.
