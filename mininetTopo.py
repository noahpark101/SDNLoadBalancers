import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import RemoteController

net = None

class TreeTopo(Topo):		
	def __init__(self):
		# Initialize topology
		Topo.__init__(self)

	def getContents(self, contents):
		hosts = contents[0]
		switch = contents[1]
		links = contents[2]
		linksInfo = contents[3:]
		return hosts, switch, links, linksInfo

	def build(self):
		"Create custom topo."
		# k = int(input("Enter value of k for fat tree topology: "))
		k = 4
		print('k = ' + str(k))

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
					self.addLink(host_addr, switch_addr, bw=10, delay='5ms', loss=1, max_queue_size=1000, use_htb=True)

		# Edge to aggregation links
		for pod_num in range(k):
			for edge_num in range(k // 2):
				edge_addr = f"10.{pod_num}.{edge_num}.1"
				for agg_num in range(k // 2, k):
					agg_addr = f"10.{pod_num}.{agg_num}.1"
					self.addLink(edge_addr, agg_addr, bw=10, delay='5ms', loss=1, max_queue_size=1000, use_htb=True)
		
		# Aggregation to core links
		for pod_num in range(k):
			for core_num in range(k // 2, k):
				agg_addr = f"10.{pod_num}.{core_num}.1"
				for i in range(1, (k // 2) + 1):
					core_addr = f"10.{k}.{core_num - (k // 2) + 1}.{i}"
					self.addLink(agg_addr, core_addr)
            
	# You can write other functions as you need.

	# Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

	# Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

	# Add links
	# > self.addLink([HOST1], [HOST2])

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()
    controllerIP = sys.argv[1]

    global net
    net = Mininet(topo=topo, link = TCLink,
                  controller=lambda name: RemoteController(name, ip=controllerIP),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    # Create QoS and queues for each ethernet port for each switch
    for switch in net.switches:
        for intf in switch.intfList():
            if 'eth' not in intf.name: continue
            
            # Making default speed 10Mbps 
            link_speed = 1000000 * 10
            prem_min = int(0.8 * link_speed)
            norm_max = int(0.5 * link_speed)
            
            # Create QoS Queues
            # os.system(f"sudo ovs-vsctl -- set Port {intf.name} qos=@newqos "
            #         f"-- --id=@newqos create QoS type=linux-htb other-config:max-rate={link_speed} queues=1=@q1,2=@q2 "
            #         f"-- --id=@q1 create queue other-config=min-rate={prem_min} "
            #         f"-- --id=@q2 create queue other-config=max-rate={norm_max} ")
            # info(f"Queues created for {intf.name}\n")

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')



if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)


    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
		
	# Command: sudo python3 mininetTopo.py 0.0.0.0:6633
