import argparse
import csv
import os.path
import random
import signal
import sqlite3
import sys
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import yaml
from basePLC import BasePLC
import importlib.util

from wacsim import py3_logger
import threading
import pandas as pd
from entities.control import AboveControl, BelowControl, TimeControl


class Error(Exception):
    """Base class for exceptions in this module."""


class TagDoesNotExist(Error):
    """Raised when tag you are looking for does not exist"""


class InvalidControlValue(Error):
    """Raised when tag you are looking for does not exist"""


class DatabaseError(Error):
    """Raised when not being able to connect to the database"""


class GenericScada(BasePLC):
    """
    This class represents a scada. This scada knows what plcs it is collecting data from by reading the
    yaml file at intermediate_yaml_path and looking at the plcs.
    """

    DB_TRIES = 20
    """Amount of times a db query will retry on a exception"""

    SCADA_CACHE_UPDATE_TIME = 2
    """ Time in seconds the SCADA server updates its cache"""

    PLC_UPDATE_TIMEOUT_TICK = 0.2
    """ Time in seconds the SCADA server waits to update a PLC cache"""

    PLC_UPDATE_TIMEOUT_TICKS_NUMBER = 29
    """ Number of ticks to wait for PLC update"""

    def __init__(self, intermediate_yaml_path):
        with intermediate_yaml_path.open() as yaml_file:
            self.intermediate_yaml = yaml.load(yaml_file, Loader=yaml.FullLoader)

        self.logger = py3_logger.get_logger(self.intermediate_yaml['log_level'])
        self.output_path = Path(self.intermediate_yaml["output_path"]) / "scada_values.csv"
        self.output_path.touch(exist_ok=True)
        self.mode = self.intermediate_yaml["mode"]
        self.iterations = self.intermediate_yaml["iterations"]
        # Create state from db values
        state = {
            'name': "plant",
            'path': self.intermediate_yaml['db_path']
        }

        # Create server, real tags are generated
        scada_server = {
            'address': self.intermediate_yaml['scada']['local_ip'],
            'tags': self.generate_real_tags(self,self.intermediate_yaml['plcs'])
        }

        # Create protocol
        scada_protocol = {
            'name': 'enip',
            'mode': 1,
            'server': scada_server
        }

        # Simple data has PLC tags, without the index (T101, 1) becomes T101
        self.plc_data, self.simple_plc_data = self.generate_plcs()
        self.controls =[]

        self.decision_maker = {}

        if 'decision_maker_per_scadacommand' in self.intermediate_yaml:
            self.logger.debug("%%%%^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
            """[{'actuators': [{'name': 'P79', 'tie_breaker': 'plc'}], 'name': 'PLC1'}, 
            {'actuators': [{'name': 'P1', 'tie_breaker': 'scada'}], 'name': 'PLC4'}]
            """

            for plc in self.intermediate_yaml['decision_maker_per_scadacommand']:

                    for actuator in plc.get('actuators', []):
                        # Add the actuator name and tie_breaker to tie_solver
                        self.decision_maker[actuator['name']] = actuator['decision_maker']

        self.logger.debug(f'Scada has decision_maker: {self.decision_maker}')
        self.logger.debug("%%%%^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

        for PLC in self.intermediate_yaml['plcs']:
            if 'sensors' not in PLC:
                PLC['sensors'] = list()

            if 'actuators' not in PLC:
                PLC['actuators'] = list()
            if self.mode=='scadacontrol' or self.mode=='hybridcontrol':
                if 'controls' in PLC:
                    for control in PLC['controls']:
                        self.logger.debug(control)
                        self.controls.append(control)


        self.controls = create_controls(self.controls) # Stav

        #self.logger.debug(self.intermediate_yaml)
        self.logger.debug('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')

        self.update_cache_flag = False
        self.plcs_ready = False

        columns_list = ['iteration', 'timestamp', 'error_flag']
        columns_list.extend(self.get_scada_tags())

        self.cache = pd.DataFrame(columns=columns_list)
        self.cache.loc[0] = 0

        # Flag used to ensure that we do not have empty rows in the scada_values.csv file
        ip_list = []
        for ip in self.plc_data:
            ip_list.append(ip)
        self.updated_plc = pd.DataFrame(index=range(self.iterations+1), columns=ip_list).fillna(False)
        self.scada_run = True



        self.do_super_construction(scada_protocol, state)


    def do_super_construction(self, scada_protocol, state):
        """
        Function that performs the super constructor call to SCADAServer
        Introduced to better facilitate testing
        """
        super(GenericScada, self).__init__(name='scada', state=state, protocol=scada_protocol)

    def get_scada_tags(self):
        aux_scada_tags = []
        for PLC in self.intermediate_yaml['plcs']:

            # We were having ordering issues by adding it as a set. Probably could be done in a more pythonic way
            if 'sensors' in PLC:
                for sensor in PLC['sensors']:
                    if sensor not in aux_scada_tags:
                        aux_scada_tags.append(sensor)

            if 'actuators' in PLC:
                for actuator in PLC['actuators']:
                    if actuator not in aux_scada_tags:
                        aux_scada_tags.append(actuator)

            if self.mode=='scadacontrol' or self.mode=='hybridcontrol':
                for actuator in self.intermediate_yaml['actuators']:
                    if f'ScadaCommand_{actuator["name"]}' not in aux_scada_tags:
                        aux_scada_tags.append(f'ScadaCommand_{actuator["name"]}')

        # self.logger.debug('SCADA tags: ' + str(aux_scada_tags))
        return aux_scada_tags

    @staticmethod
    def generate_real_tags(self,plcs):
        """
        Generates real tags with all sensors and actuators attached to plcs in the network.
        :param plcs: list of plcs
        """
        real_tags = []

        for plc in plcs:
            if 'sensors' not in plc:
                plc['sensors'] = list()

            if 'actuators' not in plc:
                plc['actuators'] = list()

            for sensor in plc['sensors']:
                if sensor != "":
                    real_tags.append((sensor, 1, 'REAL'))
                    real_tags.append((f'{sensor}S', 1, 'REAL')) # STAV 7.4 adding the S to the name so that we can do mitm on the value that is sent to the PLCs by the scada aswell
            for actuator in plc['actuators']:
                if actuator != "":
                    real_tags.append((actuator, 1, 'REAL'))
        if self.mode=='scadacontrol' or self.mode=='hybridcontrol':
            for actuator in self.intermediate_yaml['actuators']:
                    real_tags.append((f'ScadaCommand_{actuator["name"]}', 1, 'REAL'))

        self.logger.debug("--------SCADA real tags-----------")
        self.logger.debug('SCADA real tags: ' + str(real_tags))
        self.logger.debug("--------SCADA real tags-----------")

        return tuple(real_tags)

    @staticmethod
    def generate_tags(taggable):
        """
        Generates tags from a list of taggable entities (sensor or actuator)
        :param taggable: a list of strings containing names of things like tanks, pumps, and valves
        """
        tags = []

        if taggable:
            for tag in taggable:
                if tag and tag != "":
                    tags.append((tag, 1))

        return tags

    def pre_loop(self, sleep=0.5):
        """
        The pre loop of a SCADA. In which setup actions are started.
        :param sleep:  (Default value = 0.5) The time to sleep after setting everything up
        """
        self.logger.debug('SCADA enters pre_loop')
        self.db_sleep_time = random.uniform(0.01, 0.1)



        signal.signal(signal.SIGINT, self.sigint_handler)
        signal.signal(signal.SIGTERM, self.sigint_handler)

        self.keep_updating_flag = True
        self.cache_update_process = None

        time.sleep(sleep)

    def db_query(self, query, write=False, parameters=None):
        """
        Execute a query on the database
        On a :code:`sqlite3.OperationalError` it will retry with a max of :code:`DB_TRIES` tries.
        Before it reties, it will sleep for :code:`DB_SLEEP_TIME` seconds.
        This is necessary because of the limited concurrency in SQLite.
        :param query: The SQL query to execute in the db
        :type query: str
        :param write: Boolean flag to indicate if this query will write into the database
        :param parameters: The parameters to put in the query. This must be a tuple.
        :raise DatabaseError: When a :code:`sqlite3.OperationalError` is still raised after
           :code:`DB_TRIES` tries.
        """
        for i in range(self.DB_TRIES):
            try:
                with sqlite3.connect(self.intermediate_yaml["db_path"]) as conn:
                    cur = conn.cursor()
                    if parameters:
                        cur.execute(query, parameters)
                    else:
                        cur.execute(query)
                    conn.commit()

                    if not write:
                        return cur.fetchone()[0]
                    else:
                        return
            except sqlite3.OperationalError as exc:
                self.logger.info(
                    "Failed to connect to db with exception {exc}. Trying {i} more times.".format(
                        exc=exc, i=self.DB_TRIES - i - 1))
                time.sleep(self.db_sleep_time)

        self.logger.error("Failed to connect to db. Tried {i} times.".format(i=self.DB_TRIES))
        raise DatabaseError("Failed to get master clock from database")
        
    def get_sync(self, flag):
        """
        Get the sync flag of this plc.
        On a :code:`sqlite3.OperationalError` it will retry with a max of :code:`DB_TRIES` tries.
        Before it reties, it will sleep for :code:`DB_SLEEP_TIME` seconds.
        :return: False if physical process wants the plc to do a iteration, True if not.
        :raise DatabaseError: When a :code:`sqlite3.OperationalError` is still raised after
           :code:`DB_TRIES` tries.
        """
        res = self.db_query("SELECT flag FROM sync WHERE name IS ?", False, ('scada',))
        return res == flag

    def set_sync(self, flag):
        """
        Set this plcs sync flag in the sync table. When this is 1, the physical process
        knows this plc finished the requested iteration.
        On a :code:`sqlite3.OperationalError` it will retry with a max of :code:`DB_TRIES` tries.
        Before it reties, it will sleep for :code:`DB_SLEEP_TIME` seconds.
        :param flag: True for sync to 1, False for sync to 0
        :type flag: bool
        :raise DatabaseError: When a :code:`sqlite3.OperationalError` is still raised after
           :code:`DB_TRIES` tries.
        """
        self.db_query("UPDATE sync SET flag=? WHERE name IS ?", True, (int(flag), 'scada',))

    def stop_cache_update(self):
        self.update_cache_flag = False

    def sigint_handler(self, sig, frame):
        """
        Shutdown protocol for the scada, writes the output before exiting.
        """
        self.stop_cache_update()
        self.write_output()
        self.scada_run = False
        self.logger.debug("SCADA shutdown")
        sys.exit(0)

    def write_output(self):
        """
        Writes the csv output of the scada
        """
        results = self.cache
        results.to_csv(self.output_path, index=False)

    def generate_plcs(self):
        """
        Generates a list of tuples, the first part being the ip of a PLC,
        and the second  being a list of tags attached to that PLC.
        """
        plcs = OrderedDict()
        plcs_simple_tags = OrderedDict()

        for PLC in self.intermediate_yaml['plcs']:
            if 'sensors' not in PLC:
                PLC['sensors'] = list()

            if 'actuators' not in PLC:
                PLC['actuators'] = list()

            tags = []
            simple_tags = []

            tags.extend(self.generate_tags(PLC['sensors']))
            tags.extend(self.generate_tags(PLC['actuators']))



            simple_tags.extend(PLC['sensors'])
            simple_tags.extend(PLC['actuators'])


            plcs[PLC['public_ip']] = tags
            plcs_simple_tags[PLC['public_ip']] = simple_tags

        return plcs, plcs_simple_tags

    def get_master_clock(self):
        """
        Get the value of the master clock of the physical process through the database.
        On a :code:`sqlite3.OperationalError` it will retry with a max of :code:`DB_TRIES` tries.
        Before it reties, it will sleep for :code:`DB_SLEEP_TIME` seconds.
        :return: Iteration in the physical process.
        :raise DatabaseError: When a :code:`sqlite3.OperationalError` is still raised after
           :code:`DB_TRIES` tries.
        """
        master_time = self.db_query("SELECT time FROM master_time WHERE id IS 1", False, None)
        return master_time

    def update_cache(self, lock, cache_update_time):
        """
        Update SCADA cache by requesting only missing values.
        Prevents redundant tag fetches while keeping synchronization intact.
        """
        for i in range(1):
            clock = self.clock
            stale_plcs = [ip for ip in self.plc_data if not self.updated_plc.loc[clock,ip]]
            self.logger.debug("Stale_plcs: " + str(stale_plcs))
            if not stale_plcs:  # If all PLCs are updated, wait instead of looping
                continue
            self.cache.loc[clock, 'iteration'] = clock
            for plc_ip in stale_plcs:
                try:
                    values = self.receive_multiple(self.plc_data[plc_ip], plc_ip)
                    values_float = [float(x) for x in values]

                    if len(values_float) == len(self.simple_plc_data[plc_ip]):
                        with lock:
                            self.cache.loc[clock, self.simple_plc_data[plc_ip]] = values_float
                            self.updated_plc.loc[clock, plc_ip] = True  # Mark PLC as updated
                except Exception as e:
                    self.logger.error(
                        f"PLC receive_multiple with tags {self.plc_data[plc_ip]} from {plc_ip} failed: {e}"
                    )
                    

    def get_plc_updated_flags(self):
        # self.logger.debug(self.updated_plc)
        return all(value == True for value in self.updated_plc.loc[self.clock])

    def main_loop(self, sleep=0.5, test_break=False):
        """
        The main loop of a PLC. In here all the controls will be applied.
        :param sleep:  (Default value = 0.5) Not used
        :param test_break:  (Default value = False) used for unit testing, breaks the loop after one iteration
        """
        self.logger.debug("SCADA enters main_loop")
        lock = None

        while self.scada_run:
            while not self.get_sync(0):
                time.sleep(self.db_sleep_time)

            self.clock = int(self.get_master_clock())
            clock = self.clock    
            self.logger.debug(self.clock)
            self.set_sync(1)
            while not self.get_sync(2):
                pass
            if not self.plcs_ready:
                self.plcs_ready = True
                self.logger.debug("SCADA starting update cache thread")
                lock = threading.Lock()
            self.update_cache(lock, self.SCADA_CACHE_UPDATE_TIME)
                
            self.logger.debug('Finished waiting')
            master_time = datetime.now()
            self.cache.loc[self.clock, 'timestamp'] = master_time

            if self.mode=='scadacontrol' or self.mode=='hybridcontrol':
                #PLCTags = self.cache.loc[clock]
                ControlsActions = []
                SkipNextActuatorList=set() # This is to keep track of the actuators that have been applied this round, so if we use a custom algorithm we don't apply the same actuator twice as opposed to a rule based system which has two rules for one actuator and it check it twice
                for control in self.controls:
                    """self.logger.debug(f'This control is dependent on: {control.dependant}')
                    self.logger.debug(f'This control is dependent on: {control.value}')
                    self.logger.debug(f'This control is dependent on: {control.actuator}')
                    self.logger.debug(f'This control is dependent on: {control.action}')"""

                    if control.actuator in self.decision_maker:
                        HybridAction = self.decision_maker[control.actuator]
                    else:
                        HybridAction = 'rule'

                    if HybridAction == 'rule':
                        ControlsActions.append((control.actuator,control.getScadaDecision(self.cache.loc[clock][control.dependant],self.get_master_clock())))
                    else:
                        """Input: 5.0
                                timestamp           2024-07-23 17:37:31.270250
                                P79                                        1.0
                                ScadaCommand_P79                           NaN
                                ScadaCommand_P1                            NaN
                                T41                                   4.269386
                                T42                                   3.857387
                                P1                                         1.0
                                Output: closed | open
                                """

                        if control.actuator in SkipNextActuatorList:
                            continue
                        else:
                            ScriptName = HybridAction.split('/')[-1]
                            spec = importlib.util.spec_from_file_location(ScriptName, HybridAction)
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[ScriptName] = module
                            spec.loader.exec_module(module)
                            AlgoRun = getattr(module, 'AlgoRun')
                            result = AlgoRun(self.cache.loc[clock]) # Result is either 'closed' or 'open' or 'rule'

                            if isinstance(result, tuple):
                                result,SkipNextControlActuator= result
                                if SkipNextControlActuator:
                                    SkipNextActuatorList.add(control.actuator)

                            if result == 'rule':
                                ControlsActions.append((control.actuator,control.getScadaDecision(self.cache.loc[clock][control.dependant],self.get_master_clock())))
                            else:
                                ControlsActions.append((control.actuator,result,self.get_master_clock()))  # send the value of the dependant tag to the control to make a Scada decision



                    if self.mode=='hybridcontrol': # STAV 7.4 sending the value of the dependant tag so the PLCs can also get it and make a decision
                        """self.logger.debug("\n\n here sending from Scada \n\n"
                                          "control.dependant: " + control.dependant + "\n"
                                          "PLCTags[control.dependant]: " + str(self.cache.loc[clock][control.dependant]) + "\n" )"""
                        #self.set((f'{control.dependant}S',1), PLCTags[control.dependant])
                        self.send((f'{control.dependant}S',1), self.cache.loc[clock][control.dependant], self.intermediate_yaml['scada']['local_ip']) #
                        # testing 19.2 the addition of S to the name so that we can do mitm on the value that is sent to the PLCs by the scada aswell
                self.logger.debug("-----------ControlsActions--------")
                self.logger.debug(ControlsActions) # [('P79', None), ('P79', 'closed'), ('P1', None), ('P1', 'closed')]
                self.logger.debug("-----------ControlsActions--------")

                #Decision has been made, now we need to apply the decision by sending the action to the PLCs

                for action in ControlsActions: #set the action to the PLCs , now the PLCs can receive the action and apply it
                    #self.logger.debug(action)

                    if action[1] =='closed': #The Getter and Setter are working!
                        self.set((f'ScadaCommand_{action[0]}',1), 0)
                    elif action[1] =='open':
                        self.set((f'ScadaCommand_{action[0]}',1), 1)


                    UpdatedValue=self.get((f'ScadaCommand_{action[0]}',1))
                    #self.logger.debug(UpdatedValue)
                    self.cache.loc[clock, f'ScadaCommand_{action[0]}'] = UpdatedValue
                    self.send((f'ScadaCommand_{action[0]}',1), UpdatedValue, self.intermediate_yaml['scada']['local_ip']) # OMG it works! I can send the action to the PLCs




                self.logger.debug("setting sync to 25")
                self.set_sync(25) # This is the flag that tells the physical process that the SCADA has made a decision and sent the action to the PLCs
                #self.logger.debug("set sync to 25")

            self.cache.loc[clock, 'error_flag'] = False
            for ip in self.plc_data:
                if self.cache.loc[clock, self.simple_plc_data[ip]].isnull().any():
                    self.logger.debug("Missing Data From: " + str(ip))
                    self.cache.loc[clock, 'error_flag'] = True
                    # If any PLC values are empty, use previous value
                    self.cache.loc[clock, self.simple_plc_data[ip]] = self.cache.loc[
                        clock - 1, self.simple_plc_data[ip]]
            # Save scada_values.csv when needed
            if 'saving_interval' in self.intermediate_yaml and clock != 0 and \
                    clock % self.intermediate_yaml['saving_interval'] == 0:
                self.write_output()

            self.set_sync(3)
            self.logger.debug("Scada VALUES STAV")
            self.logger.debug(self.cache.loc[clock])
            self.logger.debug("Scada VALUES STAV")

            if test_break:
                break


def create_controls(controls_list):
    """
    Generates list of control objects for a plc
    :param controls_list: a list of the control dicts to be converted to Control objects
    """
    ret = []
    for control in controls_list:
        if control["type"].lower() == "above":
            control_instance = AboveControl(control["actuator"], control["action"],
                                            control["dependant"],
                                            control["value"])
            ret.append(control_instance)
        if control["type"].lower() == "below":
            control_instance = BelowControl(control["actuator"], control["action"],
                                            control["dependant"],
                                            control["value"])
            ret.append(control_instance)
        if control["type"].lower() == "time":
            control_instance = TimeControl(control["actuator"], control["action"],
                                           control["value"])
            ret.append(control_instance)
    return ret


def is_valid_file(parser_instance, arg):
    """
    Verifies whether the intermediate yaml path is valid.
    :param parser_instance: instance of argparser
    :param arg: the path to check
    """
    if not os.path.exists(arg):
        parser_instance.error(arg + " does not exist.")
    else:
        return arg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start everything for a scada')
    parser.add_argument(dest="intermediate_yaml",
                        help="intermediate yaml file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))

    args = parser.parse_args()

    plc = GenericScada(intermediate_yaml_path=Path(args.intermediate_yaml))
