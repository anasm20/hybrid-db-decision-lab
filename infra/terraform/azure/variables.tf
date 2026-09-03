variable "location" { type = string default = "westeurope" }
variable "prefix" { type = string default = "hybriddblab" }
variable "admin_username" { type = string default = "azureuser" }
variable "ssh_public_key" { type = string sensitive = true }
