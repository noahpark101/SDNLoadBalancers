import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import RemoteController

class TriangleTopo(Topo):
    def __init__(self):
        Topo.__init__(self)

    def build(self):
        bw = 10
        #Hosts
        h1 = self.addHost("h1", cpu=0.5/4, ip='10.0.0.1/24')
        h2 = self.addHost("h2", cpu=0.5/4, ip='10.0.0.2/24')
        h3 = self.addHost("h3", cpu=0.5/4, ip='10.0.0.3/24')
        h4 = self.addHost("h4", cpu=0.5/4, ip='10.0.0.4/24')
        #Switches
        s1 = self.addSwitch('s1', dpid='0000000000000001')
        s2 = self.addSwitch('s2', dpid='0000000000000002')
        s3 = self.addSwitch('s3', dpid='0000000000000003')
        s4 = self.addSwitch('s4', dpid='0000000000000004')
        # Main traffic
        self.addLink(h1, s1, bw = bw)
        self.addLink(h2, s4, bw = bw)

        # Background load traffic
        self.addLink(h3, s1, bw = bw)
        self.addLink(h4, s4, bw = bw)

        # Core links (shared)
        self.addLink(s1, s2, bw = bw)
        self.addLink(s1, s3, bw = bw)
        self.addLink(s2, s4, bw = bw)
        self.addLink(s3, s4, bw = bw)
            
            


def startNetwork():
	info('** Creating the tree network\n')
	topo = TriangleTopo()
	controllerIP = sys.argv[1]
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
