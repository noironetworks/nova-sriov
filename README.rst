# nova-sriov
This repo contains code that uses Nova's monkey-patch functionality to
enable SRIOV NIC selection when scheduling instances.

The monkey-patch feature provides decorators to all methods in a module, by specifying
the full module path and the full decorator path.  This feature is supported through
the queens release, but is dropped in Rocky, where an alternate means of providing
SRIOV NIC selection should become available.

The following is an example of how this would be configured:
[DEFAULT]
...
monkey_patch=True
monkey_patch_modules=nova_sriov_nics.patch_nova:opflexagent.patch_nova.dummy_decorator

This patch must be applied to to the nova-api server.

The following describes the workflow for SRIOV NIC selection in Nova:
1) Make sure that nova.conf for a given nova-compute has pci_passthrough_whitelist configuration, which places each SRIOV NIC on its own physnet (in /etc/nova/nova.conf):
[DEFAULT]
....
pci_passthrough_whitelist={"devname": "10gb1", "physical_network":"physnet2"}
pci_passthrough_whitelist={"devname": "10gb0", "physical_network":"physnet1"}

The above maps SRIOV NIC 10gb0 to physnet1 and SRIOV NIC 10gb1 to physnet2.

2) The SRIOV agent on that same host for that nova-compute has configuration for eth physnets it supports (e.g. in /etc/neutron/plugins/ml2/sriov_agent.ini):
[sriov_nic]
physical_device_mappings = physnet1:10gb0,physnet1:10gb1

In this case, only a single physnet is used. Note that the NIC to physnet mapping information is NOT consistent with the mapping information provided in nova.conf from step 1 -- this is intentional

3) User creates a neutron VLAN type network, using the provider extensions. They assign it a physnet and VLAN -- say physnet1 and VLAN 101:
# neutron net-create --provider:network_type vlan --provider:physical_network phsynet1 --provider:segmentation_id 101 foonet

4) User creates a neutron port that they want to use for a VM to enable SRIOV. They add the "vnic_type" attribute of "direct" to indicate SRIOV, and also add the "binding:profile" attribute, populated with a "physical_network" property. In this case, a different physnet from the network's physnet is used (i.e. physnet2 instead of physnet1)

# neutron port-create foonet --name demo1 --binding:vnic_type direct --binding:profile type=dict physical_network=physnet2

5) User boots a VM, passing the UUID of the port that was created in step 4:
# nova boot --flavor m1.small --image centos --nic port-id=98d210a9-24e5-4d7f-9068-f26dfd7656fb  --availability-zone ovs test_demo1
