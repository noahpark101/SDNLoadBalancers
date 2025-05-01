import sys
import os

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_forest
import pox.openflow.spanning_tree as spanning_tree

from pox.lib.revent import *
from pox.lib.util import dpid_to_str, dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
import networkx as nx

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.graph = nx.Graph()
        self.link_to_port = {}


    def _handle_LinkEvent(self, event):
        link = event.link
        switch1 = dpid_to_str(link.dpid1)
        switch2 = dpid_to_str(link.dpid2)
        port1 = event.link.port1
        port2 = event.link.port2
        self.link_to_port[(switch1, switch2)] = port1
        self.link_to_port[(switch2, switch1)] = port2
        self.graph.add_edge(switch1, switch2, port1=port1, port2=port2)

        log.info(f"Link detected between {switch1} and {switch2} from {port1} to {port2}")

    def _handle_ConnectionUp(self, event):
        switch_name = dpid_to_str(event.dpid)
        log.info(f"Switch {switch_name} connected.")
        # Add switch to the topology
        self.graph.add_node(switch_name)

        #TODO:
        #Check to see if the switch is connected to hosts, if so add hosts as node into graph and add the edges too
        #Also, do the txt file thing

    
    def _handle_PacketIn (self, event):
        def flood (message = None):
            msg = of.ofp_packet_out()
            msg.data = event.ofp

            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            event.connection.send(msg)
            log.info("Flooding")

        def forward (message = None):
            packet = event.parsed.find('ipv4')
            if not packet:
                return
            

        forward()




def launch():
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    core.registerNew(Controller)

