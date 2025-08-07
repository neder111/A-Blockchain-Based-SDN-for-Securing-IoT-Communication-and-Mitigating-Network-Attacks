from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, arp, tcp, udp
import hashlib
import json
import datetime
import time
import re
from collections import defaultdict
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class Block:
    def __init__(self, index, timestamp, data, previous_hash, signature):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.signature = signature
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.signature}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def serialize(self):
        return json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': json.loads(self.data),
            'previous_hash': self.previous_hash,
            'signature': self.signature,
            'hash': self.hash
        }).encode()


class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    BLOCKCHAIN_FILE = "/tmp/blockchain.json"
    RATE_LIMIT = 10  # packets/sec per MAC

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.blockchain = []
        genesis_block = Block(0, str(datetime.datetime.now()), "Genesis Block", "0", "GENESIS_SIGNATURE")
        self.blockchain.append(genesis_block)
        self.save_blockchain_to_file()
        self.logger.info("Genesis block created")

        self.private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        self.public_key = self.private_key.public_key()

        self.mac_to_port = {}
        self.trusted_flows = {}
        self.packet_counters = defaultdict(lambda: {'count': 0, 'start_time': time.time()})
        self.ip_mac_table = defaultdict(dict)  # dpid -> {ip: mac}

    def save_blockchain_to_file(self):
        chain_data = [{
            'index': b.index,
            'timestamp': b.timestamp,
            'data': json.loads(b.data) if b.index != 0 else b.data,
            'previous_hash': b.previous_hash,
            'signature': b.signature,
            'hash': b.hash
        } for b in self.blockchain]

        with open(self.BLOCKCHAIN_FILE, "w") as f:
            json.dump(chain_data, f, indent=2)

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst,
                                idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 10, match_icmp, actions)

        match_all = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match_all, actions)

        self.logger.info("Switch features handled - flow rules installed")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        start_time = time.time()
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        src_mac = eth.src
        dst_mac = eth.dst

        # DDoS Rate Limiting
        now = time.time()
        window = self.packet_counters[src_mac]
        if now - window['start_time'] > 1:
            window['count'] = 0
            window['start_time'] = now
        window['count'] += 1
        if window['count'] > self.RATE_LIMIT:
            self.logger.warning(f"DDoS prevention: Blocking {src_mac} on port {in_port}")
            match = parser.OFPMatch(in_port=in_port, eth_src=src_mac)
            actions = []
            self.add_flow(datapath, 100, match, actions, idle_timeout=60)
            return

        # ARP Spoofing Detection
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            ip = arp_pkt.src_ip
            mac = arp_pkt.src_mac
            if ip in self.ip_mac_table[dpid]:
                if self.ip_mac_table[dpid][ip] != mac:
                    self.logger.warning(f"ARP spoofing detected: {ip} used by both {self.ip_mac_table[dpid][ip]} and {mac}")
                    match = parser.OFPMatch(eth_type=0x0806, arp_spa=ip, eth_src=mac)
                    actions = []
                    self.add_flow(datapath, 100, match, actions, idle_timeout=120)
                    return
            else:
                self.ip_mac_table[dpid][ip] = mac

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        out_port = self.mac_to_port[dpid].get(dst_mac, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)

        protocol_type = None
        dst_port = None

        if ip_pkt:
            if tcp_pkt:
                dst_port = tcp_pkt.dst_port
                if dst_port == 1883:
                    protocol_type = "MQTT"
                elif dst_port == 5672:
                    protocol_type = "AMQP"
                elif dst_port == 80:
                    protocol_type = "HTTP"
                else:
                    protocol_type = f"TCP/{dst_port}"
            elif udp_pkt:
                dst_port = udp_pkt.dst_port
                if dst_port == 5683:
                    protocol_type = "CoAP"
                else:
                    protocol_type = f"UDP/{dst_port}"

        if ip_pkt and protocol_type:
            flow_key = (src_mac, ip_pkt.src, protocol_type, dst_port)
            if flow_key in self.trusted_flows:
                if in_port != self.trusted_flows[flow_key]:
                    self.logger.warning(f"Replay attack detected: {flow_key}")
                    return
            else:
                self.trusted_flows[flow_key] = in_port

            # Smart Contract: Drop based on temp/humidity in MQTT payload
            drop_due_to_contract = False
            if protocol_type == "MQTT":
                payload = msg.data.decode(errors='ignore')
                temp_match = re.search(r'temp[:=]\s*(\d+)', payload)
                hum_match = re.search(r'hum[:=]\s*(\d+)', payload)
                if temp_match and hum_match:
                    temp = int(temp_match.group(1))
                    hum = int(hum_match.group(1))
                    if temp < 50 and (hum < 30 or hum > 70):
                        self.logger.warning(f"SmartContract: Dropping packet: temp={temp}, hum={hum}")
                        drop_due_to_contract = True
            if drop_due_to_contract:
                return

            # Blockchain data
            now_dt = datetime.datetime.now()
            latency_us = int((time.time() - start_time) * 1_000_000)
            data_dict = {
                "protocol": protocol_type,
                "src_ip": ip_pkt.src,
                "dst_ip": ip_pkt.dst,
                "dst_port": dst_port,
                "timestamp": str(now_dt),
                "latency_us": latency_us,
                "in_port": in_port
            }

            block_size = self.add_blockchain_entry(data_dict)
            self.logger.info(f"Blockchain-secured packet size: {block_size} bytes")

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)

    def add_blockchain_entry(self, data_dict):
        json_data = json.dumps(data_dict)
        signature = self.private_key.sign(json_data.encode(), ec.ECDSA(hashes.SHA256()))
        signature_hex = signature.hex()

        last_block = self.blockchain[-1]
        temp_block = Block(
            index=last_block.index + 1,
            timestamp=str(datetime.datetime.now()),
            data=json_data,
            previous_hash=last_block.hash,
            signature=signature_hex
        )

        block_size_bytes = len(temp_block.serialize())
        data_dict["packet_size_bytes"] = block_size_bytes

        final_block_data = json.dumps(data_dict)
        final_block = Block(
            index=temp_block.index,
            timestamp=temp_block.timestamp,
            data=final_block_data,
            previous_hash=temp_block.previous_hash,
            signature=temp_block.signature
        )

        self.blockchain.append(final_block)
        self.logger.info(f"Blockchain block #{final_block.index} added: {data_dict}")
        self.save_blockchain_to_file()
        return block_size_bytes

