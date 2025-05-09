import os
import sys
import atexit
from time import sleep
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
        s5 = self.addSwitch('s5', dpid='0000000000000005')
        s6 = self.addSwitch('s6', dpid='0000000000000006')
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

        self.addLink(s1, s5, bw = bw)
        self.addLink(s5, s6, bw = bw)
        self.addLink(s6, s4, bw = bw)

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

    # BENCHMARKING SCRIPT
    info('** Starting the benchmark\n')
    h1, h2, h3, h4 = net.get('h1', 'h2', 'h3', 'h4')

    # Run iperf servers for h2/h4
    h2.cmd('iperf -s &')
    h4.cmd('iperf -s &')
    sleep(5) # Wait for controller to finish

    # Run experiment in background
    info('** Starting background traffic\n')
    h3.cmd('iperf -c {} -P 8 -t 25 > h3_to_h4.txt &'.format(h4.IP()))
    sleep(5)
    info('** Starting actual traffic\n')
    h1.cmd('iperf -c {} -P 4 -t 20 > h1_to_h2.txt &'.format(h2.IP()))
    info('** Wait for results')
    sleep(25) # Wait for results

    info("*** Results:\n")
    info("h1 -> h2:\n")
    info(h1.cmd('cat h1_to_h2.txt'))
    info('** End of benchmark\n')

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
