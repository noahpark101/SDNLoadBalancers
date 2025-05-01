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

    def _handle_ConnectionUp(self, event):
        log.info(f"Switch {event.dpid} connected.")
        # Add switch to the topology
        self.graph.add_node(event.dpid)
    
    def _handle_PacketIn (self, event):
        packet = event.parsed.find('ipv4')
        if not packet:
            return
        
        src_ip, dst_ip = packet.src_ip, packet.dst_ip



def launch():
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    core.registerNew(Controller)

