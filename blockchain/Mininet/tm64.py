from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch, RemoteController

class MyTopo(Topo):
    def build(self):
        switches = []
        hosts = []

        # Create switches
        for i in range(1, 65):
            switch = self.addSwitch(f's{i}', cls=OVSKernelSwitch, protocols='OpenFlow13')
            switches.append(switch)

        # Create hosts
        for i in range(1, 65):
            host = self.addHost(f'h{i}', cpu=1.0/20, mac=f"00:00:00:00:00:{i:02}", ip=f"10.0.0.{i}/24")
            hosts.append(host)

        # Connect each host to all switches
        for i, switch in enumerate(switches):
            self.addLink(hosts[i], switch)

        # Connect switches in a mesh topology
        for i in range(len(switches)):
            for j in range(i+1, len(switches)):
                self.addLink(switches[i], switches[j])

def startNetwork():
    topo = MyTopo()
    c0 = RemoteController('c0', ip='127.0.0.1', port=6653)
    net = Mininet(topo=topo, link=TCLink, controller=c0)

    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    startNetwork()

