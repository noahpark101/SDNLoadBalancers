import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import RemoteController


class FatTree(Topo):
	"Topology for Question 2."
	def __init__(self):
		Topo.__init__(self)
	
	def build(self):
		k = int(sys.argv[1])
		info(f"Building FatTree k = {k}")

		# Add core switches
		for i in range(1, 3):
			for j in range(1, (k // 2) + 1):
				self.addSwitch(f"10.{k}.{i}.{j}", dpid=f"00:00:00:00:00:{k:02}:{i:02}:{j:02}")
		
		# Add pod (aggregate/edge) switches
		for pod_num in range(k):
			for switch_num in range(k):
				self.addSwitch(f"10.{pod_num}.{switch_num}.1", dpid=f"00:00:00:00:00:{pod_num:02}:{switch_num:02}:01")

		# Add hosts, and host-edge links
		for pod_num in range(k):
			for switch_num in range(k // 2):
				switch_addr = f"10.{pod_num}.{switch_num}.1"
				for host_num in range(2, (k // 2) + 2):
					host_addr = f"10.{pod_num}.{switch_num}.{host_num}"
					self.addHost(host_addr, cpu=.5/4)
					self.addLink(host_addr, switch_addr, bw=10)

		# Edge to aggregation links
		for pod_num in range(k):
			for edge_num in range(k // 2):
				edge_addr = f"10.{pod_num}.{edge_num}.1"
				for agg_num in range(k // 2, k):
					agg_addr = f"10.{pod_num}.{agg_num}.1"
					self.addLink(edge_addr, agg_addr, bw=10)
		
		# Aggregation to core links
		for pod_num in range(k):
			for core_num in range(k // 2, k):
				agg_addr = f"10.{pod_num}.{core_num}.1"
				for i in range(1, (k // 2) + 1):
					core_addr = f"10.{k}.{core_num - (k // 2) + 1}.{i}"
					self.addLink(agg_addr, core_addr)

		#TODO:
			#make it so that you write to a textfile of the switch_name host_name port_number
			#afterwards, for control.py -> write the function to read the textfile to create a dictionary of key: (switch, host) value: port number
				#NOTE: control.py is called first, so it will probably error -> keep trying until it works
def startNetwork():
	info('** Creating the tree network\n')
	topo = FatTree()
	controllerIP = sys.argv[2]
	global net
	net = Mininet(topo=topo, link = TCLink,
                  controller=lambda name: RemoteController(name, ip=controllerIP),
                  listenPort=6633, autoSetMacs=True)
	info('** Starting the network\n')
	net.start()
	info('** Running CLI\n')
	CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()


if __name__ == '__main__':

    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)


    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
