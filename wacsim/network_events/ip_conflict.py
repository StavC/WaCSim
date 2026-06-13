import os
import subprocess
import sys

from wacsim.network_events.synced_event import SyncedEvent
import argparse
from pathlib import Path


class IPConflict(SyncedEvent):
    """
    This is an IP conflict network event. It simulates duplicate IP address
    resolution conflicts by toggling packet drop probability on the target link
    between 0% and 100% on alternate iterations.

    :param intermediate_yaml_path: The path to the intermediate YAML file
    :param yaml_index: The index of the event in the intermediate YAML
    :param interface_name: The name of the interface that has the event
    """

    def __init__(self, intermediate_yaml_path: Path, yaml_index: int, interface_name: str):
        super().__init__(intermediate_yaml_path, yaml_index)
        self.interface_name = interface_name
        self.step_counter = 0

    def set_loss(self, percent):
        cmd = 'tc qdisc del dev ' + str(self.interface_name) + ' root'
        os.system(cmd)
        if percent > 0:
            cmd = f'tc qdisc add dev {self.interface_name} root netem loss {percent}%'
            os.system(cmd)

    def setup(self):
        self.logger.debug("Starting IP conflict at interface " + str(self.interface_name))
        self.step_counter = 0
        self.set_loss(100)

    def teardown(self):
        cmd = 'tc qdisc del dev ' + str(self.interface_name) + ' root '
        os.system(cmd)
        self.logger.info("Tear down network event")

    def interrupt(self):
        if self.state == 1:
            self.teardown()

    def event_step(self):
        self.step_counter += 1
        if self.step_counter % 2 == 1:
            self.logger.debug(f"IP conflict step {self.step_counter}: dropping packets (100% loss)")
            self.set_loss(100)
        else:
            self.logger.debug(f"IP conflict step {self.step_counter}: channel clear (0% loss)")
            self.set_loss(0)


def is_valid_file(parser_instance, arg):
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist")
    else:
        return arg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start IP conflict event')
    parser.add_argument(dest="intermediate_yaml",
                        help="intermediate yaml file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network event in intermediate yaml",
                        type=int,
                        metavar="N")
    parser.add_argument(dest="interface_name", help="Interface name of the network event")

    args = parser.parse_args()

    event = IPConflict(intermediate_yaml_path=Path(args.intermediate_yaml), yaml_index=args.index,
                       interface_name=args.interface_name)
    event.main_loop()
