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
        self.switch_to_host = {
            "00-00-00-00-00-01" : "10.0.0.1",
            "00-00-00-00-00-04" : "10.0.0.2",
            "00-00-00-00-00-04" : "10.0.0.4"
        }
        self.host_to_switch = {
            "10.0.0.1" : "00-00-00-00-00-01",
            "10.0.0.2" : "00-00-00-00-00-04",
            "10.0.0.4" : "00-00-00-00-00-04"
        }
        self.switch_host_to_port = {}


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

    
    def _handle_PacketIn (self, event):
        def flood (message = None):
            msg = of.ofp_packet_out()
            msg.data = event.ofp

            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            event.connection.send(msg)
            log.info("Flooding")

        def install (port, packet, switch_dpid):
            dst_ip = packet.find('ipv4').dstip
            match = of.ofp_match()
            msg = of.ofp_flow_mod()
            msg.match = match
            msg.match.nw_dst = dst_ip
            msg.command = of.OFPFC_ADD
            msg.match.dl_type = 0x800
            msg.match.nw_proto = 6
            msg.priority = 800
            #create actions
            msg.actions.append(of.ofp_action_output(port = port))
            event.connection.send(msg)
            print(f"NEW FLOW RULE: port: {port} for switch: {switch_dpid} for dst ip : {dst_ip}")

            #don't forget to send out msg to manually route packet once too
            msg2 = of.ofp_packet_out()
            msg2.data = event.ofp
            msg2.actions.append(of.ofp_action_output(port = port))
            event.connection.send(msg2)
            log.info(f"Sent message to manually route packet that caused PacketIn")


        def forward (message = None):
            log.info("PacketIn Event Received")
            log.info(event.parsed)
            packet = event.parsed.find('ipv4')
            if event.parsed.find('arp'):
                flood()
            if not packet:
                return
            switch_dpid = dpid_to_str(event.dpid)
            src_ip = str(packet.srcip)
            dst_ip = str(packet.dstip)
            port = event.port
            dst_switch_dpid = self.host_to_switch[dst_ip]
            #Update switch to host port mapping if you can
            if switch_dpid in self.switch_to_host:
                self.switch_host_to_port[(switch_dpid, src_ip)] = port
            log.info(f"Src IP: {src_ip}")
            log.info(f"DST IP: {dst_ip}")
            log.info(f"Switch DPID: {switch_dpid}")
            #Calculate shortest path
            path = nx.shortest_path(self.graph, source = switch_dpid, target = dst_switch_dpid)
            log.info("Path below")
            log.info(path)
            #Time to send to host 
            if len(path) == 1:
                if (dst_switch_dpid, dst_ip) in self.switch_host_to_port:
                    port_to_send = self.switch_host_to_port[(dst_switch_dpid, dst_ip)]
                    install(port_to_send, packet, switch_dpid)
                    return
                flood()
                return
            #Send to next switch
            next_node = path[1]
            port_to_send = self.link_to_port[(switch_dpid, next_node)]
            install(port_to_send, packet, switch_dpid)



        forward()




def launch():
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    core.registerNew(Controller)

