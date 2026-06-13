import os
import subprocess
import sys

from wacsim.network_events.synced_event import SyncedEvent
import argparse
from pathlib import Path


class BurstyLoss(SyncedEvent):
    """
    This is a bursty loss network event. It uses Linux-tc to configure a 
    Gilbert-Elliott packet loss model (gemodel) to simulate bursty wireless
    connectivity on the link.

    :param intermediate_yaml_path: The path to the intermediate YAML file
    :param yaml_index: The index of the event in the intermediate YAML
    :param interface_name: The name of the interface that has the event
    """

    def __init__(self, intermediate_yaml_path: Path, yaml_index: int, interface_name: str):
        super().__init__(intermediate_yaml_path, yaml_index)
        self.interface_name = interface_name
        self.state_g2b = float(self.intermediate_event['state_g2b'])
        self.state_b2g = float(self.intermediate_event['state_b2g'])

    def setup(self):
        self.logger.debug("Starting bursty loss at interface " + str(self.interface_name)
                         + f" with g2b={self.state_g2b}% and b2g={self.state_b2g}%")

        cmd = 'tc qdisc del dev ' + str(self.interface_name) + ' root'
        os.system(cmd)

        cmd = f'tc qdisc add dev {self.interface_name} root netem loss gemodel {self.state_g2b}% {self.state_b2g}%'
        self.logger.debug('trying command: ' + str(cmd))
        os.system(cmd)

    def teardown(self):
        cmd = 'tc qdisc del dev ' + str(self.interface_name) + ' root '
        os.system(cmd)

        self.logger.info("Tear down network event")

    def interrupt(self):
        if self.state == 1:
            self.teardown()

    def event_step(self):
        pass


def is_valid_file(parser_instance, arg):
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist")
    else:
        return arg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start bursty loss event')
    parser.add_argument(dest="intermediate_yaml",
                        help="intermediate yaml file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument(dest="index", help="Index of the network event in intermediate yaml",
                        type=int,
                        metavar="N")
    parser.add_argument(dest="interface_name", help="Interface name of the network event")

    args = parser.parse_args()

    event = BurstyLoss(intermediate_yaml_path=Path(args.intermediate_yaml), yaml_index=args.index,
                       interface_name=args.interface_name)
    event.main_loop()
