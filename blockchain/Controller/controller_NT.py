from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp

import datetime
import time
import json
import os


class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=priority,
                                match=match,
                                instructions=inst,
                                idle_timeout=idle_timeout,
                                hard_timeout=hard_timeout)
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

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)

        proto_desc = "No IP"
        dst_port = None
        if ip_pkt:
            proto_desc = f"IP proto={ip_pkt.proto} src={ip_pkt.src} dst={ip_pkt.dst}"
            if tcp_pkt:
                proto_desc += f" TCP dst_port={tcp_pkt.dst_port}"
                dst_port = tcp_pkt.dst_port
            elif udp_pkt:
                proto_desc += f" UDP dst_port={udp_pkt.dst_port}"
                dst_port = udp_pkt.dst_port
        self.logger.info(f"PacketIn: {proto_desc}")

        if ip_pkt and ip_pkt.proto != 1:  # Ignore ICMP
            protocol_type = None

            if tcp_pkt:
                if tcp_pkt.dst_port == 1883:
                    protocol_type = "MQTT"
                elif tcp_pkt.dst_port == 5672:
                    protocol_type = "AMQP"
                elif tcp_pkt.dst_port == 80:
                    protocol_type = "HTTP"
                else:
                    protocol_type = f"TCP/{tcp_pkt.dst_port}"

            elif udp_pkt:
                if udp_pkt.dst_port == 5683:
                    protocol_type = "CoAP"
                else:
                    protocol_type = f"UDP/{udp_pkt.dst_port}"

            if protocol_type:
                now = datetime.datetime.now()
                packet_size = len(msg.data)
                latency_us = int((time.time() - start_time) * 1_000_000)  # microseconds

                data = {
                    "dst_ip": ip_pkt.dst,
                    "dst_port": dst_port,
                    "latency_us": latency_us,
                    "packet_size_bytes": packet_size,
                    "protocol": protocol_type,
                    "src_ip": ip_pkt.src,
                    "timestamp": str(now)
                }

                # Append to JSON list file for Flask
                json_file = "/tmp/latest_packets.json"

                if os.path.exists(json_file):
                    with open(json_file, "r") as f:
                        try:
                            packet_list = json.load(f)
                        except json.JSONDecodeError:
                            packet_list = []
                else:
                    packet_list = []

                packet_list.append(data)

                MAX_ENTRIES = 1000  # limit to last 50 entries
                if len(packet_list) > MAX_ENTRIES:
                    packet_list = packet_list[-MAX_ENTRIES:]

                with open(json_file, "w") as f:
                    json.dump(packet_list, f, indent=2)

                self.logger.info(f"Data appended: {json.dumps(data)}")

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)

