from mininet.topo import Topo

class Question2Topo(Topo):
	"Topology for Question 2."
	
	def build(self):
		"Create custom topo."

		k = int(input("Enter value of k for fat tree topology: "))
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

topos = {
	'q2_topo': (lambda: Question2Topo())
}
