#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova import exception
from nova.network import model as network_model
from nova.network.neutronv2 import api


if not hasattr(api.API, 'NOVA_SRIOV_PHYSNET_PATCHED'):
    def patched_get_phynet_info(self, context, neutron, net_id, port=None):
        phynet_name = None
        if self._has_multi_provider_extension(context, neutron=neutron):
            network = neutron.show_network(net_id,
                                           fields='segments').get('network')
            segments = network.get('segments', {})
            for net in segments:
                # NOTE(vladikr): In general, "multi-segments" network is a
                # combination of L2 segments. The current implementation
                # contains a vxlan and vlan(s) segments, where only a vlan
                # network will have a physical_network specified, but may
                # change in the future. The purpose of this method
                # is to find a first segment that provides a physical network.
                # TODO(vladikr): Additional work will be required to handle the
                # case of multiple vlan segments associated with different
                # physical networks.
                phynet_name = net.get('provider:physical_network')
                if phynet_name:
                    return phynet_name
            # Raising here as at least one segment should
            # have a physical network provided.
            if segments:
                msg = (_("None of the segments of network %s provides a "
                         "physical_network") % net_id)
                raise exception.NovaException(message=msg)

        net = neutron.show_network(net_id,
                        fields='provider:physical_network').get('network')
        if port and port.get('binding:profile'):
            phynet_name = port['binding:profile'].get('physical_network',
                net.get('provider:physical_network'))
        else:
            phynet_name = net.get('provider:physical_network')
        return phynet_name

    def patched_get_port_vnic_info(self, context, neutron, port_id):
        """Retrieve port vnic info

        Invoked with a valid port_id.
        Return vnic type and the attached physical network name.
        """
        phynet_name = None
        port = self._show_port(context, port_id, neutron_client=neutron,
                               fields=['binding:vnic_type',
                                       'binding:profile', 'network_id'])
        vnic_type = port.get('binding:vnic_type',
                             network_model.VNIC_TYPE_NORMAL)
        if vnic_type in network_model.VNIC_TYPES_SRIOV:
            net_id = port['network_id']
            phynet_name = self._get_phynet_info(context, neutron, net_id,
                                                port=port)
        return vnic_type, phynet_name

    api.API._get_phynet_info = patched_get_phynet_info
    api.API._get_port_vnic_info = patched_get_port_vnic_info
    setattr(api.API, '_get_phynet_info', patched_get_phynet_info)
    setattr(api.API, '_get_port_vnic_info', patched_get_port_vnic_info)
    setattr(api.API, 'NOVA_SRIOV_PHYSNET_PATCHED', True)


def dummy_decorator(name, fn):
    """Dummy decorator which is used from utils.monkey_patch().

        :param name: name of the function
        :param fn: - object of the function
        :returns: fn -- decorated function

    """
    def wrapped_func(*args, **kwarg):
        return fn(*args, **kwarg)
    return wrapped_func


class DummyClass(object):
    """Dummy class used as a means of patching nova's neutron API
     code.
     """

    def __init__(self, *args, **kwargs):
        pass

    def dummy_method(self, *args, **kwargs):
        pass
