import argparse
import os
import sys
import numpy as np
from pathlib import Path
from scapy.layers.inet import IP, TCP
from scapy.packet import Raw

from wacsim.network_attacks.mitm_netfilter_queue_subprocess import PacketQueue
from wacsim.network_attacks.utilities import translate_payload_to_float, translate_float_to_payload
from wacsim.network_attacks.mitm_netfilter_queue import extract_tag_name

class NoiseInjectionNetfilterQueue(PacketQueue):
    """
    Noise injection netfilter queue worker. Maps TCP connections to targeted tags
    and applies math-based noise on the response payloads on the network.
    """
    def __init__(self, intermediate_yaml_path: Path, yaml_index: int, queue_number: int):
        super().__init__(intermediate_yaml_path, yaml_index, queue_number)
        self.attacked_tags = self.intermediate_attack['tags']
        self.connection_tags = {}
        self.attacker_cache = {}

    def apply_noise(self, tag_config, sensor_value):
        scale = float(tag_config['scale'])
        noise_type = tag_config.get('noise_type', 'gaussian')
        
        if scale == 0:
            return sensor_value

        if noise_type == 'gaussian':
            return sensor_value + np.random.normal(0, scale * sensor_value)
        elif noise_type == 'gaussian_absolute':
            return sensor_value + np.random.normal(0, scale)
        elif noise_type == 'uniform':
            return sensor_value + np.random.uniform(-scale * sensor_value, scale * sensor_value)
        elif noise_type == 'percentage':
            return sensor_value * (1 + np.random.uniform(-scale, scale))
        elif noise_type == 'drift':
            try:
                iteration = int(self.get_master_clock())
            except Exception:
                iteration = 0
            return sensor_value + scale * iteration
        else:
            return sensor_value

    def capture(self, packet):
        try:
            p = IP(packet.get_payload())
            if 'TCP' in p and Raw in p:
                payload = p[Raw].load
                tag_name = extract_tag_name(payload)
                
                if tag_name:
                    self.attacker_cache[tag_name] = translate_payload_to_float(payload)
                
                # Check if it is a request packet to map the TCP connection
                if len(p) > 105 and tag_name:
                    for tag in self.attacked_tags:
                        if tag_name == tag['tag']:
                            client_ip = p[IP].src
                            client_port = p[TCP].sport
                            self.connection_tags[(client_ip, client_port)] = tag
                            self.logger.debug(f"Connection {client_ip}:{client_port} mapped to tag {tag_name}")

                # Modify the matching response packet
                elif len(p) == 102:
                    client_ip = p[IP].dst
                    client_port = p[TCP].dport
                    if (client_ip, client_port) in self.connection_tags:
                        tag_config = self.connection_tags[(client_ip, client_port)]
                        tag_name = tag_config['tag']
                        base_value = translate_payload_to_float(payload)
                        
                        modified_value = self.apply_noise(tag_config, base_value)
                        
                        p[Raw].load = translate_float_to_payload(modified_value, payload)
                        # Recalculate checksums
                        del p[IP].chksum
                        del p[TCP].chksum
                        packet.set_payload(bytes(p))
                        self.logger.debug(f"Injected noise on tag '{tag_name}' response: original={base_value:.4f}, modified={modified_value:.4f}")
                        del self.connection_tags[(client_ip, client_port)]
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
    parser = argparse.ArgumentParser(description='Start Noise Injection NetfilterQueue')
    parser.add_argument(dest="intermediate_yaml",
                        help="Intermediate YAML file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate YAML",
                        type=int, metavar="N")
    parser.add_argument(dest="number", help="Number of the queue configured in IP Tables",
                        type=int, metavar="N")

    args = parser.parse_args()

    attack = NoiseInjectionNetfilterQueue(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index,
        queue_number=args.number
    )
    attack.main_loop()
