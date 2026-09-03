resource "azurerm_resource_group" "lab" { name = "${var.prefix}-rg" location = var.location }
resource "azurerm_virtual_network" "lab" { name = "${var.prefix}-vnet" address_space = ["10.42.0.0/16"] location = azurerm_resource_group.lab.location resource_group_name = azurerm_resource_group.lab.name }
resource "azurerm_subnet" "lab" { name = "lab" resource_group_name = azurerm_resource_group.lab.name virtual_network_name = azurerm_virtual_network.lab.name address_prefixes = ["10.42.1.0/24"] }
resource "azurerm_public_ip" "vm" { name = "${var.prefix}-pip" location = azurerm_resource_group.lab.location resource_group_name = azurerm_resource_group.lab.name allocation_method = "Static" sku = "Standard" }
resource "azurerm_network_security_group" "vm" { name = "${var.prefix}-nsg" location = azurerm_resource_group.lab.location resource_group_name = azurerm_resource_group.lab.name
  security_rule { name="ssh" priority=100 direction="Inbound" access="Allow" protocol="Tcp" source_port_range="*" destination_port_range="22" source_address_prefix="*" destination_address_prefix="*" }
}
resource "azurerm_network_interface" "vm" { name="${var.prefix}-nic" location=azurerm_resource_group.lab.location resource_group_name=azurerm_resource_group.lab.name
  ip_configuration { name="internal" subnet_id=azurerm_subnet.lab.id private_ip_address_allocation="Dynamic" public_ip_address_id=azurerm_public_ip.vm.id }
}
resource "azurerm_network_interface_security_group_association" "vm" { network_interface_id=azurerm_network_interface.vm.id network_security_group_id=azurerm_network_security_group.vm.id }
resource "azurerm_linux_virtual_machine" "vm" { name="${var.prefix}-vm" resource_group_name=azurerm_resource_group.lab.name location=azurerm_resource_group.lab.location size="Standard_B2s" admin_username=var.admin_username network_interface_ids=[azurerm_network_interface.vm.id]
  admin_ssh_key { username=var.admin_username public_key=var.ssh_public_key }
  os_disk { caching="ReadWrite" storage_account_type="StandardSSD_LRS" }
  source_image_reference { publisher="Canonical" offer="0001-com-ubuntu-server-jammy" sku="22_04-lts-gen2" version="latest" }
}
