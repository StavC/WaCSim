import sys

import pandas as pd
import wntr
from antlr4 import *

from wacsim.parser.antlr.controlsLexer import controlsLexer
from wacsim.parser.antlr.controlsParser import controlsParser
from wacsim.py3_logger import get_logger

class Error(Exception):
    """Base class for exceptions in this module."""


class NoInpFileGiven(Error):
    """Raised when tag you are looking for does not exist"""


class NotEnoughInitialValues(Error):
    """Raised when there are not enough initial values in a csv"""


def value_to_status(actuator_value):
    """
    Translates int corresponding to actuator status.

    :param actuator_value: The value from the status.value of the actuator
    :type actuator_value: int
    """
    if actuator_value == 0:
        return "closed"
    else:
        return "open"


class InputParser:
    """
    Class handling the parsing of .inp input files.

    :param intermediate_yaml: The intermediate yaml file
    """

    def __init__(self, intermediate_yaml):
        """Constructor method"""
        self.data = intermediate_yaml

        self.logger = get_logger(self.data['log_level'])

        for plc in self.data['plcs']:
            if 'sensors' not in plc:
                plc['sensors'] = list()
            if 'dependent_sensors' not in plc and 'dependant_sensors' not in plc:
                plc['dependent_sensors'] = list()
            if 'actuators' not in plc:
                plc['actuators'] = list()

        # Get the INP file path
        if 'inp_file' in self.data.keys():
            self.inp_file_path = self.data['inp_file']
        else:
            raise NoInpFileGiven()
        # Read the inp file with WNTR

        self.wn = wntr.network.WaterNetworkModel(self.inp_file_path)

        self.batch_mode = 'batch_simulations' in self.data

    def write(self):
        """
        Writes all needed inp file sections into the intermediate_yaml.
        """
        # Generate PLC controls
        self.generate_controls()
        # Add dependent sensors from decision_maker config (if any)
        self.add_decision_maker_dependents()
        # Create synthetic controls for actuators with custom algorithms but no INP controls
        self.generate_synthetic_controls_for_custom_algorithms()
        # Generate list of actuators + initial values
        self.generate_actuators_list()
        # Generate list of times
        self.generate_times()
        # Generate initial values if batch mode is true
        # This being true means the user configured initial tank levels
        # If this is false, we need to initialize the tank values with the ones configured in the EPANET file
        if 'initial_tank_data' in self.data:
            self.generate_initial_tank_values()
        else:
            self.data["initial_tank_values"] = {}
        # Generate network loss values if network loss is true
        if 'network_loss_data' in self.data:
            self.generate_network_losses()
        # Generate network delay values if network delay is true
        if 'network_delay_data' in self.data:
            self.generate_network_delays()
        # Add iterations if not existing
        if 'network_jitter_data' in self.data:
            self.generate_network_jitters()
        if 'noise_scale_data' in self.data:
            self.generate_noise_scales()
        if "iterations" not in self.data.keys():
            iterations = int(self.data["time"][0]["duration"] / self.data["time"][1]["hydraulic_timestep"])
            if iterations <= 0:
                print(f"Error in inp file section [TIMES]: (duration: {self.data['time'][0]['duration']} / "
                      f"hydraultic timestep: {self.data['time'][1]['hydraulic_timestep']}) = {iterations}")
                sys.exit(1)
            self.data["iterations"] = iterations

        # Return the YAML object
        return self.data

    def generate_controls(self):
        """
        Generates list of controls with their types, values, actuators, and
        potentially dependant; then adds that to self.data to be written to the yaml.
        """
        input_file = FileStream(self.inp_file_path)
        tree = controlsParser(CommonTokenStream(controlsLexer(input_file))).controls()
        #self.logger.debug('Controls tree')
        controls = []
        for i in range(0, tree.getChildCount()):
            child = tree.getChild(i)
            # Get all common control values from the control
            actuator = str(child.getChild(2))
            action = str(child.getChild(4))

            if action == 'OPEN' or action == 'CLOSED':
                action_aux = action.lower()
            else:
                action_aux = float(action)

            if str(child.getChild(8)) == 'NODE':
                # This is an AT NODE control
                dependant = str(child.getChild(10))
                value = float(str(child.getChild(14)))
                
                controls.append({
                    "type": str(child.getChild(12)).lower(),
                    "dependant": dependant,
                    "value": value,
                    "actuator": actuator,
                    "action": action_aux
                })

                #self.logger.debug('control:\n' + str(controls[-1]))

            if str(child.getChild(8)) == 'TIME':
                # This is a TIME control
                value = float(str(child.getChild(10)))
                controls.append({
                    "type": "time",
                    "value": int(value),
                    "actuator": actuator,
                    "action": action_aux,
                })

        for plc in self.data['plcs']:
            plc['controls'] = []
            actuators = plc['actuators']
            for control in controls:
                if control['actuator'] in actuators:
                    plc['controls'].append(control)

    def add_decision_maker_dependents(self):
        """
        Adds dependent sensors from decision_maker_per_plc and decision_maker_per_scadacommand
        configurations to the appropriate PLCs' dependent_sensors list.
        This ensures custom algorithms have access to the sensors they need.
        
        Now supports 'dependents' as a required list of sensor names.
        """
        # Handle PLC mode decision makers
        if 'decision_maker_per_plc' in self.data and self.data['decision_maker_per_plc']:
            for dm_plc in self.data['decision_maker_per_plc']:
                # Find the matching PLC in plcs list
                for plc in self.data['plcs']:
                    if plc['name'] == dm_plc['name']:
                        # Process each actuator's decision maker
                        for actuator_config in dm_plc.get('actuators', []):
                            if 'dependents' in actuator_config:
                                dependents_list = actuator_config['dependents']
                                # Add each dependent to the PLC's sensor list
                                for dependent in dependents_list:
                                    # Add to dependent_sensors if not already present
                                    if 'dependent_sensors' in plc:
                                        if dependent not in plc['dependent_sensors']:
                                            plc['dependent_sensors'].append(dependent)
                                            self.logger.debug(f"Added dependent sensor '{dependent}' to PLC '{plc['name']}' for custom algorithm on actuator '{actuator_config['name']}'")
                                    elif 'dependant_sensors' in plc:
                                        if dependent not in plc['dependant_sensors']:
                                            plc['dependant_sensors'].append(dependent)
                                            self.logger.debug(f"Added dependent sensor '{dependent}' to PLC '{plc['name']}' for custom algorithm on actuator '{actuator_config['name']}'")
                        break

        # Handle SCADA mode decision makers
        if 'decision_maker_per_scadacommand' in self.data and self.data['decision_maker_per_scadacommand']:
            for dm_plc in self.data['decision_maker_per_scadacommand']:
                # Find the matching PLC in plcs list
                for plc in self.data['plcs']:
                    if plc['name'] == dm_plc['name']:
                        # Process each actuator's decision maker
                        for actuator_config in dm_plc.get('actuators', []):
                            if 'dependents' in actuator_config:
                                dependents_list = actuator_config['dependents']
                                # Add each dependent to the PLC's sensor list
                                for dependent in dependents_list:
                                    # Add to dependent_sensors if not already present
                                    if 'dependent_sensors' in plc:
                                        if dependent not in plc['dependent_sensors']:
                                            plc['dependent_sensors'].append(dependent)
                                            self.logger.debug(f"Added dependent sensor '{dependent}' to PLC '{plc['name']}' for custom algorithm on actuator '{actuator_config['name']}'")
                                    elif 'dependant_sensors' in plc:
                                        if dependent not in plc['dependant_sensors']:
                                            plc['dependant_sensors'].append(dependent)
                                            self.logger.debug(f"Added dependent sensor '{dependent}' to PLC '{plc['name']}' for custom algorithm on actuator '{actuator_config['name']}'")
                        break

    def generate_synthetic_controls_for_custom_algorithms(self):
        """
        Creates synthetic TIME controls for actuators that have custom decision makers
        but no control rules defined in the INP file.
        
        These synthetic controls:
        - Create TWO TIME controls: one at time 0 (start) and one at last iteration (end)
        - This ensures the actuator is in the control loop throughout the simulation
        - The custom algorithm will execute and override these controls at every iteration
        - Dependents list is required and all sensors are registered
        """
        # Get simulation duration from WNTR network
        duration = self.wn.options.time.duration
        hydraulic_timestep = self.wn.options.time.hydraulic_timestep
        
        # Calculate last iteration time
        last_iteration = int(duration)
        
        # Collect all decision makers from both PLC and SCADA modes
        decision_makers = {}
        
        # Handle PLC mode decision makers
        if 'decision_maker_per_plc' in self.data and self.data['decision_maker_per_plc']:
            for dm_plc in self.data['decision_maker_per_plc']:
                plc_name = dm_plc['name']
                if plc_name not in decision_makers:
                    decision_makers[plc_name] = {}
                for actuator_config in dm_plc.get('actuators', []):
                    decision_makers[plc_name][actuator_config['name']] = {
                        'decision_maker': actuator_config.get('decision_maker'),
                        'dependents': actuator_config.get('dependents', [])
                    }
        
        # Handle SCADA mode decision makers
        if 'decision_maker_per_scadacommand' in self.data and self.data['decision_maker_per_scadacommand']:
            for dm_plc in self.data['decision_maker_per_scadacommand']:
                plc_name = dm_plc['name']
                if plc_name not in decision_makers:
                    decision_makers[plc_name] = {}
                for actuator_config in dm_plc.get('actuators', []):
                    decision_makers[plc_name][actuator_config['name']] = {
                        'decision_maker': actuator_config.get('decision_maker'),
                        'dependents': actuator_config.get('dependents', [])
                    }
        
        # For each PLC, check if actuators with decision makers need synthetic controls
        for plc in self.data['plcs']:
            plc_name = plc['name']
            if plc_name not in decision_makers:
                continue
                
            # Get existing controls for this PLC
            existing_control_actuators = set()
            if 'controls' in plc:
                for control in plc['controls']:
                    existing_control_actuators.add(control['actuator'])
            
            # Check each actuator with a decision maker
            for actuator_name, dm_info in decision_makers[plc_name].items():
                # Skip if this actuator already has a control from INP file
                if actuator_name in existing_control_actuators:
                    continue
                
                # Skip if decision_maker is 'rule', 'scada', 'open', or 'closed' (not a custom algorithm)
                dm_value = dm_info['decision_maker']
                if dm_value in ['rule', 'scada', 'open', 'closed']:
                    continue
                
                # This actuator needs synthetic TIME controls
                dependents_list = dm_info['dependents']
                
                # Create TWO TIME controls to span the simulation
                # Control 1: At time 0 (start) - set to OPEN
                synthetic_control_start = {
                    "type": "time",
                    "value": 0,
                    "actuator": actuator_name,
                    "action": "open"
                }
                
                # Control 2: At last iteration (end) - set to CLOSED
                synthetic_control_end = {
                    "type": "time",
                    "value": last_iteration,
                    "actuator": actuator_name,
                    "action": "closed"
                }
                
                # Add both controls to the PLC's controls
                if 'controls' not in plc:
                    plc['controls'] = []
                plc['controls'].append(synthetic_control_start)
                plc['controls'].append(synthetic_control_end)
                
                self.logger.info(f"Created synthetic TIME controls for actuator '{actuator_name}' "
                               f"in PLC '{plc_name}' (time 0 to {last_iteration}) with dependents {dependents_list} for custom algorithm")

    def generate_times(self):
        """
        Generates duration and hydraulic timestep and adds to the
        data to be written to the yaml file.
        """
        times = [
            {"duration": self.wn.options.time.duration},
            {"hydraulic_timestep": self.wn.options.time.hydraulic_timestep}
        ]
        self.data['time'] = times

    def generate_actuators_list(self):
        """
        Generates list of actuators with their initial states
        and adds to the data to be written to the yaml file.
        """

        pumps = []
        valves = []

        for pump in self.wn.pumps():
            pumps.append({
                "name": pump[0],
                "initial_state": value_to_status(pump[1].status.value)
            })
        for valve in self.wn.valves():
            valves.append({
                "name": valve[0],
                "initial_state": value_to_status(valve[1].status.value)
            })
        # Append valves to pumps
        pumps.extend(valves)
        self.data['actuators'] = pumps

    def read_initial_tank_values_from_inp(self):
        """ Reads the tank values from the EPANET inp file"""
        show = False
        tank_tuples = []
        with open(self.inp_file_path) as infile:
            for line in infile:
                if show and line.startswith('['):
                    show = False
                if show == True:
                    split_line = line.split()
                    if len(split_line) > 1:
                        tank_tuples.append((split_line[0], split_line[2]))
                if line.startswith('[TANKS]'):
                    show = True
                    continue
        del tank_tuples[0]
        self.data['initial_tank_values'] = dict(tank_tuples)

    def generate_initial_tank_values(self):
        """Generates all tanks with their initial values if the user configured them in the yaml file"""

        initial_values = {}
        initial_tank_levels = pd.read_csv(self.data['initial_tank_data'])
        self.verify_csv_input(initial_tank_levels, 'initial_tank_data')
        # For all columns in csv
        for index in range(len(initial_tank_levels.columns)):
            name = initial_tank_levels.columns[index]
            # Insert tank value into data
            data_index = self.data["batch_index"] if self.batch_mode else 0
            initial_values[str(name)] = \
                float(initial_tank_levels.iloc[data_index, index])

        self.data['initial_tank_values'] = initial_values

    def generate_network_losses(self):
        """Generates list of routers with their network losses from the input csv"""

        network_loss = {}
        network_loss_data = pd.read_csv(self.data['network_loss_data'])
        self.verify_csv_input(network_loss_data, 'network_loss_data')
        # For all columns in csv
        for index in range(len(network_loss_data.columns)):
            name = network_loss_data.columns[index]
            # Insert loss  value into data
            data_index = self.data["batch_index"] if self.batch_mode else 0
            network_loss[str(name)] = \
                float(network_loss_data.iloc[data_index, index])

        self.data['network_loss_values'] = network_loss

    def generate_network_delays(self):
        """Generates list of routers with their network delays from the input csv"""

        network_delay = {}
        network_delay_data = pd.read_csv(self.data['network_delay_data'])
        self.verify_csv_input(network_delay_data, 'network_delay_data')
        # For all columns in csv
        for index in range(len(network_delay_data.columns)):
            name = network_delay_data.columns[index]
            # Insert tank : value into data
            data_index = self.data["batch_index"] if self.batch_mode else 0
            network_delay[str(name)] = \
                str(network_delay_data.iloc[data_index, index]) + "ms"

        self.data['network_delay_values'] = network_delay

    def generate_network_jitters(self):
        """Generates list of routers with their network jitter from the input csv"""

        network_jitter = {}
        network_jitter_data = pd.read_csv(self.data['network_jitter_data'])
        self.verify_csv_input(network_jitter_data, 'network_jitter_data')
        # For all columns in csv
        for index in range(len(network_jitter_data.columns)):
            name = network_jitter_data.columns[index]
            # Insert tank : value into data
            data_index = self.data["batch_index"] if self.batch_mode else 0
            network_jitter[str(name)] = \
                str(network_jitter_data.iloc[data_index, index]) + "ms"

        self.data['network_jitter_values'] = network_jitter
        
    def generate_noise_scales(self):
        """Generates list of routers with their network jitter from the input csv"""

        noise_scale = {}
        noise_scale_data = pd.read_csv(self.data['noise_scale_data'])
        self.verify_csv_input(noise_scale_data, 'noise_scale_data')
        # For all columns in csv
        for index in range(len(noise_scale_data.columns)):
            name = noise_scale_data.columns[index]
            # Insert tank : value into data
            data_index = self.data["batch_index"] if self.batch_mode else 0
            noise_scale[str(name)] = \
                float(noise_scale_data.iloc[data_index, index])
        self.data['noise_scale_data'] = noise_scale

    def verify_csv_input(self, dataframe, data):
        """
        Verifies the csv files have the proper number of rows for a simulation

        :param dataframe: pandas dataframe containing csv data
        :param data: name of data that is being verified
        """
        num_rows = len(dataframe)
        if self.batch_mode:
            if num_rows < self.data['batch_simulations']:
                raise NotEnoughInitialValues("Provided csv has fewer rows than number of batch simulations: " + data)
        else:
            if num_rows <= 0:
                raise NotEnoughInitialValues("Provided csv has no data: " + data)
