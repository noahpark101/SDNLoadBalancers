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
from collections import defaultdict
from pox.lib.recoco import Timer
from queue import PriorityQueue

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.graph = nx.Graph()
        self.link_to_port = {}
        self.switch_to_host = {
            "00-00-00-00-00-01" : ["10.0.0.1", "10.0.0.3"],
            "00-00-00-00-00-04" : ["10.0.0.2", "10.0.0.0"]
        }
        self.host_to_switch = {
            "10.0.0.1" : "00-00-00-00-00-01",
            "10.0.0.3" : "00-00-00-00-00-01",
            "10.0.0.2" : "00-00-00-00-00-04",
            "10.0.0.4" : "00-00-00-00-00-04"
        }
        self.switch_host_to_port = {}
        self.link_to_load = defaultdict(int)

        # basically this keeps tracking of path to use next -> (to get next path int % num_of_paths)
        self.src_dst_path_counter = defaultdict(int) # key: (src, dst) value: integer

        # keeps track for a given (src, dst, TCP port) what path is being used for it
        # needed because you need stay use same path as you install flow entries 1 by 1
        self.src_dst_tcp_port_to_path = {} # key: (src, dst, TCP port) value: int (path num)

        self.switch_port_to_dest_switch = {}
        self.link_load = defaultdict(int)  # key: (src_switch, dst_switch) → load
        Timer(5, self._request_stats, recurring=True)

    def _request_stats(self):
        self.link_load.clear()
        for connection in core.openflow._connections.values():
            connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

    def _handle_LinkEvent(self, event):
        link = event.link
        switch1 = dpid_to_str(link.dpid1)
        switch2 = dpid_to_str(link.dpid2)
        port1 = event.link.port1
        port2 = event.link.port2
        self.link_to_port[(switch1, switch2)] = port1
        self.link_to_port[(switch2, switch1)] = port2
        self.graph.add_edge(switch1, switch2, port1=port1, port2=port2)

        # (switch, port) -> switch for least load
        self.switch_port_to_dest_switch[(switch1, port1)] = switch2
        self.switch_port_to_dest_switch[(switch2, port2)] = switch1
            
        log.info(f"Link detected between {switch1} and {switch2} from {port1} to {port2}")

    def _handle_ConnectionUp(self, event):
        switch_name = dpid_to_str(event.dpid)
        log.info(f"Switch {switch_name} connected.")
        # Add switch to the topology
        self.graph.add_node(switch_name)


    def get_least_loaded_path(self, all_paths):
        #PriorityQueue autosorts path by load
        pq = PriorityQueue()
        for path in all_paths:
            #for each path calculate its load and add to pq
            pq.put((self.calculate_path_load(path), path))
        #top of pq is the least loaded path
        path_load, least_loaded_path = pq.get()
        return least_loaded_path

    def calculate_path_load(self, path):
        #for each link in the path, add the transmitted bytes and take the average
        path_load = 0
        for i in range(0, len(path) - 1):
            link = (path[i], path[i + 1])
            path_load += self.link_to_load[link]
        return path_load / (len(path) - 1)

    def _handle_PortStatsReceived(self, event):
        
        dpid = dpid_to_str(event.connection.dpid)
        for stat in event.stats:
            port_num = stat.port_no
            bytes_sent = stat.tx_bytes
            #log.info(f"Port stat info: Port no: {stat.port_no} Port bytes: {stat.tx_bytes}")
            #skip ports connected to controller and hosts
            if port_num == 65534 or (dpid, port_num) not in self.switch_port_to_dest_switch:
                continue
            #get link load and store it in map
            dst_switch = self.switch_port_to_dest_switch[(dpid, port_num)]
            switch_link = (dpid, dst_switch)
            self.link_to_load[switch_link] = bytes_sent

    
    def _handle_PacketIn (self, event):
        def flood (message = None):
            msg = of.ofp_packet_out()
            msg.data = event.ofp

            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            event.connection.send(msg)
            log.info("Flooding")

        def install(port, switch_dpid):
            ip_hdr = event.parsed.find('ipv4')
            tcp_hdr = event.parsed.find('tcp')

            # Create match rule
            match = of.ofp_match()
            msg = of.ofp_flow_mod()
            msg.match = match
            msg.match.nw_src = ip_hdr.srcip
            msg.match.nw_dst = ip_hdr.dstip
            msg.match.tp_src = tcp_hdr.srcport
            msg.match.tp_dst = tcp_hdr.dstport
            msg.command = of.OFPFC_ADD
            msg.match.dl_type = 0x800
            msg.match.nw_proto = 6
            msg.priority = 800

            # Create actions
            msg.actions.append(of.ofp_action_output(port = port))
            event.connection.send(msg)
            print(f"NEW FLOW RULE: port: {port} for switch: {switch_dpid} for dst ip : {ip_hdr.dstip}")

            #don't forget to send out msg to manually route packet once too
            msg2 = of.ofp_packet_out()
            msg2.data = event.ofp
            msg2.actions.append(of.ofp_action_output(port = port))
            event.connection.send(msg2)
            log.info(f"Sent message to manually route packet that caused PacketIn")


        def forward (message = None):
            log.info("PacketIn Event Received")
            log.info(event.parsed)
            ip_hdr = event.parsed.find('ipv4')
            if event.parsed.find('arp'):
                flood()
            if not ip_hdr:
                return
            tcp_hdr = event.parsed.find('tcp')
            src_tcp = tcp_hdr.srcport
            dst_tcp = tcp_hdr.dstport
            switch_dpid = dpid_to_str(event.dpid)
            src_ip = str(ip_hdr.srcip)
            dst_ip = str(ip_hdr.dstip)
            port = event.port
            dst_switch_dpid = self.host_to_switch[dst_ip]
            #Update switch to host port mapping if you can
            if switch_dpid in self.switch_to_host:
                self.switch_host_to_port[(switch_dpid, src_ip)] = port
            log.info(f"Src IP: {src_ip}")
            log.info(f"DST IP: {dst_ip}")
            log.info(f"Switch DPID: {switch_dpid}")

            path = []

            # We have a path allocated for this TCP stream already
            if (src_ip, dst_ip, src_tcp, dst_tcp) in self.src_dst_tcp_port_to_path:
                path = self.src_dst_tcp_port_to_path[(src_ip, dst_ip, src_tcp, dst_tcp)]
                log.info("PATH already allocated")
                log.info(path)
                if switch_dpid not in path:
                    return
                start_index = path.index(switch_dpid)
                path = path[start_index:]
            else: #if we don't
                #get least loaded path
                all_paths = list(nx.all_simple_paths(self.graph, source=switch_dpid, target=dst_switch_dpid))
                path = self.get_least_loaded_path(all_paths)
                log.info("Allocating NEW PATH")
                log.info(path)
                self.src_dst_tcp_port_to_path[(src_ip, dst_ip, src_tcp, dst_tcp)] = path

            #Time to send to host 
            if len(path) == 1:
                if (dst_switch_dpid, dst_ip) in self.switch_host_to_port:
                    port_to_send = self.switch_host_to_port[(dst_switch_dpid, dst_ip)]
                    install(port_to_send, switch_dpid)
                    return
                flood()
                return
            
            #Send to next switch
            next_node = path[1]
            port_to_send = self.link_to_port[(switch_dpid, next_node)]
            install(port_to_send, switch_dpid)

        forward()

def launch():
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    core.registerNew(Controller)

