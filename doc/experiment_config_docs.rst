#########################
Experiment Config Options
#########################

.. contents:: Table of Contents
   :depth: 4
   :local:

The main experiment config files are used to define the structure of the cyber layer, simulation settings, and additional simulation data such as network losses. These setting represent the bulk of the experimental parameters, with `attack`_ and `event`_ parameters being defined in seperate config files.

Main Config Options
===================
The main experiment config file contains the parameters necessary to run the simulation, as well as optional parameters that deal directly with the simulation. It is also
the file that is used to start the simulation in the terminal.

.. code-block:: yaml

   inp_file: anytown_map.inp
   plcs: !include anytown_plcs.yaml
   network_topology_type: complex
   output_path: output
   iterations: 288
   mininet_cli: False
   log_level: info
   batch_simulations: 1
   saving_interval: 0
   demand: PDD
   noise_scale: 0.05
   network_loss_data: example_network_loss_data.csv
   network_delay_data: example_network_delay_data.csv
   initial_tank_data: example_tank_data.csv
   demand_patterns: demands_anytown.csv
   attacks: !include anytown_mitm.yaml
   events: !include anytown_nwk_event.yaml
   mode: plccontrol
   decision_maker_per_plc: !include anytown_decision_plc.yaml
   decision_maker_per_scadacommand: !include anytown_decision_scada.yaml

inp_file
--------
**(Required Option)**

**Takes file path to .INP file.**

The .INP file is the file that contains all information about the water distribution system (WDS) and the hydraulic simulation parameters for use with the `EPANET`_ hydraulic simulation engine. Besides
defining the components of the WDS (junctions, pipes, pumps, etc.) other information of importance for WaCSim included in this file are demand patterns, control rules, and the duration/hydraulic timestep
of the simulation. These files can also be opened to be edited in EPANET, or in a text editor of your choice.

plcs
-----
**(Required Option)**

**Takes file path to PLC .YAML file.**

The PLC config file specifies the number of PLCs, as well as the actuators (pumps, valves) and sensors (tanks, nodes) attached to each PLC. More information about the PLC config file can be found in it's
`documentation section`_.

Always put `!include` before the file path (E.g. ``plcs: !include anytown_plcs.yaml``).

network_topology_type
---------------------
**Takes either** ``simple`` **or** ``complex``. **(default:** ``simple`` **)**

The network topology type determines the structure of the cyber layer, and how the PLCs and SCADA system are connected. This primarily affects where attackers will sit in the network.

When set to ``simple``, both the SCADA and PLCS will be a part of one large network, with a single router handling all network traffic. Additionally, only two switches are generated, one connected
to the SCADA and another to the PLCs. This means that in a simple network topology, an attacker would be able to target all PLCs by spoofing a single router.

When set to ``complex``, the SCADA and each PLC are connected to their own individual local network. In a system with two PLCs and a SCADA system, there would be four routers, one global router
and three for each local network. This network topology is generally more realistic and is the recommended option when performing man-in-the-middle attacks.

output_path
-----------
**Takes file path to desired output destination.** **(default:** ``output`` **)**

The output path is the folder where all the results from the simulation would be saved. This path must be a relative path from where
the config file is (E.g. ``/WaCSim_results``) and not an absolute path (E.g. ``/home/user/Documents/WaCSim_results``).

iterations
----------
**Takes integer representing number of iterations to run WaCSim experiment for.** **(default: # of hydraulic timesteps)**

The number of iterations, by default is the number of hydraulic timesteps which is ``duration/hydraulic_time_step``. These values can be found in the .INP file for the network, or by opening
the .INP file in EPANET. Setting the iteration value to a number other than the default will modify the duration of the simulation, but not the hydraulic time step. For example, if by default the
simulation is 1 day with 5-minute time steps, then setting `iterations= 100` will change the duration to 8.33 hours.

mininet_cli
-----------
**Takes** ``True`` **or** ``False``. **(default:** ``False`` **)**

The mininet CLI is a tool for the mininet python package. Enabling this option with ``True`` will pause the simulation until running the command ``exit``. This can be useful for debugging but otherwise
it is not recommended to enable this option.

log_level
---------
**Takes** ``debug``, ``info``, ``warning``, ``error``, **or** ``critical``. **(default:** ``info`` **)**

The log level determines what information is shown in the terminal while the simulation is running. The following is a list of each level and what is shown:

``debug``: Debug is the lowest log level and will show all print statements and all logging events. Debug is also the only logging level that will show print statements.

``info``: The info log level will show basic information during the startup phase of the simulation, and then a progress bar that gives the elapsed time, current iteration, and estimated time to completion.

``warning``: This log level only displays warning-level log events and above. Warnings typically do not affect results and can usually be ignored but are still potentially valuable for debugging.

``error``: This log level only displays error-level log events and above. Errors may indicate that something has gone wrong with the simulation and are cause for investigation. However, they are not
always a problem.

``critical``: This log level will only display critical-level log events. Critical errors will always cause the simulation to shut down. WaCSim shutdowns are typically caused by typos or errors in the configuration
files and are the first place to check to solve them.

batch_simulations
-----------------
**Takes integer representing number of simulations to run.** **(default:** ``1`` **)**

Batch simulations are useful when wanting to run variations of an experiment with different initial tank levels, demand patterns, and network losses and/or delays. Setting ``batch_simulations`` to anything
other than ``1``, then for each simulation it will run a different set of initial conditions and save them to ``output_path/simulation_number``. When running batch simulations care should be taken that
all additional data from .CSVs (initial tank conditions, demand patterns, etc.) are structured correctly. More information on how to do this is covered under in the documentation for ``network_loss_data``, ``network_delay_data``, ``initial_tank_data``, and ``demand_patterns``.

saving_interval
---------------
**Takes integer representing save interval in iterations.** **(default:** ``0`` **)**

Setting `saving_interval` to anything other than 0 will result in the output CSV files being written while the simulation is still in progress. The value determines how often the CSV file is saved,
with the value equaling the number of iterations between saves.

An additional note is that the .PCAP files are also written in real time. This means that in conjunction with saving_interval, data from the simulation can be accessed and used for real-time applications.

demand
------
**Takes** ``PDD`` **or** ``DD``. **(default:** ``PDD`` **)**

The demand model determines how demands and pressures in the system are calculated.

Demand driven analysis (represented by ``DD``) will always ensure that demands are met at each junction. This can lead to situations where head is negative and not physically realistic. This is
the default in EPANET.

In contrast, pressure driven demand (represented by ``PDD``) allows for the demand at each junction to fluctuate with the pressure in the system. This generally prevents negative pressures
from occurring in the system but may lead to scenarios where the demand at each node is not met. For WaCSim, PDD is recommended due to the frequency of scenarios in which the system does
not behave correctly (due to an attacker) and using demand driven analysis has a higher chance of unrealistic system states.

noise_scale_data
-----------------
**Takes file path to network_delay_data .CSV file.**

The noise scale is the amount of variability in sensor measurments. This can be useful for modeling more realistic scenarios, or for modeling scenarios where a sensor is malfunctioning.

`noise_scale` should be a .CSV file, where the column headers are `scada` and/or names of PLCs. The number of non-header rows, where noise scale values are entered, should be equal to `batch_simulations` (or a single row when not doing batch simulations), with the row number corresponding to the simulation number.

Setting `noise_scale_data` to a non-zero value will result in Gaussian noise being added to the sensor values that PLCs receive and send. The exact function used is from `NumPy`_, ``np.random.normal``. Under the hood, ``noise_scale`` determines the standard deviation of the normal distribution, equal to ``noise_scale*sensor_value`` resulting in a random sample that is added to the unmodified sensor value.

network_loss_data
-----------------
**Takes file path to network_delay_data .CSV file.**

Network losses are when packets are sent but not received. Packets can be lost for a variety of reasons and can be used to represent non-ideal conditions in the simulation.

`network_loss_data` should be a .CSV file, where the column headers are `scada` and/or names of PLCs. The number of non-header rows, where network loss values are entered, should be equal to `batch_simulations` (or a single row when not doing batch simulations), with the row number corresponding to the simulation number.

Each value represents the probability (from ``0-100%``) that a given packet is lost. This is accomplished by mininet through Linux's netem module, and the documentation for this functionality is `here`_ if interested.

network_delay_data
------------------
**Takes file path to network_delay_data .CSV file.**

Network delays are when packets are delayed by some constant time, typically expressed in milliseconds. All networks have some delay, a result of needing to transmit packets across a physical distance.

`network_delay_data` should be a .CSV file, where the column headers are `scada` and/or names of PLCs. The number of non-header rows, where network delay values are entered, should be equal to `batch_simulations` (or a single row when not doing batch simulations), with the row number corresponding to the simulation number.

Each value represents the delay in milliseconds for each packet. This is accomplished by mininet through Linux's netem module, and the documentation for this functionality is `here`_ if interested.

network_jitter_data
------------------
**Takes file path to network_jitter_data .CSV file.**

Network jitter is an additional delay that is randomly selected from a normal distribution. All networks have some delay, a result of needing to transmit packets across a physical distance.

`network_jitter_data` should be a .CSV file, where the column headers are `scada` and/or names of PLCs. The number of non-header rows, where network jitter values are entered, should be equal to `batch_simulations` (or a single row when not doing batch simulations), with the row number corresponding to the simulation number.

Each value represents the jitter in milliseconds for each packet. Providing a value of 20ms, for instance, will add an additional packet delay selected from a normal distribution with a standard deviation of 20ms. This is accomplished by mininet through Linux's netem module, and the documentation for this functionality is `here`_ if interested.

initial_tank_data
-----------------
**Takes file path to initial_tank_data .CSV file.**

`network_delay_data` should be a .CSV file, where the column headers are the names of tanks. The number of non-header rows, where initial tank values are entered, should be equal to `batch_simulations` (or a single row when not doing batch simulations), with the row number corresponding to the simulation number.

Each value represents the tank level in meters.

demand_patterns
---------------
**Takes file path to demand_patterns .CSV file or folder path if doing batch simulations.**

Each demand pattern .CSV should have the column headers set to the demand pattern names, and each non-header row set to the multipliers for each demand pattern. The name of the .CSV must be the simulation number when running in batch simulation mode (``0.csv``, ``1.csv``, etc.). Additionally, when running batch simulations, the input to ``demand_patterns`` should be the folder where the .CSV files are located (E.g. ``demand_patterns: patterns/``).

attacks
-------
**Takes file path to attacks .YAML config files.**

The `attacks` option is a relative path that points to where attack configuration files are located. See the attacks config documentation for more information on attacks.

Always put `!include` before the file path (E.g. ``attacks: !include anytown_mitm.yaml``).

events
-------
**Takes file path to events .YAML config files.**

The `events` option is a relative path that points to where event configuration files are located. See the events config documentation for more information on attacks.

Always put `!include` before the file path (E.g. ``events: !include anytown_nwk_event.yaml``).

mode
----
**Takes** ``plccontrol``, ``scadacontrol``, **or** ``hybridcontrol``. **(default:** ``scadacontrol`` **)**

The mode determines which decision (open or closed) for actuators is prioritized. Decisions made depend on the local cache of the PLC/SCADA, meaning that in attack scenarios or rare cases when using ``noise_scale``, or ``network_loss_data`` the decision made can differ between the PLC and SCADA.

``plccontrol`` prioritizes the decision made by the PLC using its own local cache. In this mode, the network is especially vulnerable to cyberattacks, as attacks on PLCs will have a significant
impact.

``scadacontrol`` prioritizes the decision made by the SCADA using its own local cache. In contrast to ``plccontrol``, this mode is more resistant to simple MitM attacks that target PLCs. Unless data communication links for the SCADA are compromised (such as in a replay attack) ``scadacontrol`` will result in simple MitM attacks being thwarted.

``hybridcontrol`` allows for the use of custom logic to determine either the decision itself or which mode to use (``plccontrol`` or ``scadacontrol``). This mode opens up the possibility to test real-time strategies for detecting/resisting attacks. More on this can be found on the `Examples`_ page and the Per-PLC/Per-SCADA config options.

decision_maker_per_plc
----------------------
**Takes file path to Per-PLC decision maker .YAML config file.**

The `decision_maker_per_plc` option is a relative path that points to where Per-PLC configuration files are located. See the Per-PLC config documentation for more information.

Always put `!include` before the file path (E.g. ``decision_maker_per_plc: !include MiniAnyTown_decision_plc.yaml``).

decision_maker_per_scadacommand
-------------------------------
**Takes file path to Per-SCADA decision maker .YAML config file.**

The `decision_maker_per_scadacommand` option is a relative path that points to where Per-SCADA configuration files are located. See the Per-SCADA config documentation for more information.

Always put `!include` before the file path (E.g. ``decision_maker_per_scadacommand: !include MiniAnyTown_decision_scada.yaml``).

PLC Config Options
==================
The PLC config file is where you define the PLCs that are in the system, as well as the sensors and actuators attached to it.

.. code-block:: yaml

   - name: PLC1
     actuators:
       - P78
       - P79
   - name: PLC2
     sensors:
       - T41
   - name: PLC3
     sensors:
       - T42
 
name
----
**(Required Option)**

**Takes:** string of up to 10 characters excluding ``(space)`` and ``-`` characters.

The name of the PLC can be anything within the limitations. These names are used for, other than providing a unique identifier, generating PLC_data.csv file names.

sensors
-------
**Takes**: list of tanks, junctions, valves, and/or pumps.

The sensors listed here should use the same names as the one in the .INP file. These sensors define what sensor data is locally available to each PLC, and what other PLCs can request from it. There are no constraints or limitations on what sensors can be added to a PLC, however generally PLCs should contain sensors within a certain physical region of the network.

For pumps/valves add "F" to the end of the name as defined in the .INP file. This sensor will measure the flow at the pump/valve in meters per second. 

For tanks/juntions the sensor will measure the level/head in meters.

dependant_sensors/dependent_sensors
-----------------------------------
**Takes**: list of tanks, junctions, valves, and/or pumps.

The sensors listed here should use the same names as the one in the .INP file. These sensors define what additional sensor data this PLC should request from other PLCs. By default, the dependent sensors are only those needed by the actuators for the PLC to perform the basic rule-based controls from the .INP file. 

For pumps/valves add "F" to the end of the name as defined in the .INP file. This sensor will measure the flow at the pump/valve in meters per second. 

For tanks/juntions the sensor will measure the level/head in meters.

actuators
---------
**Takes**: list of pumps and/or valves.

The sensors listed here define which actuators are controlled PLC, and what actuator data other PLCs can request from it. There are no constraints or limitations on what actuators can be added to a PLC, however generally PLCs should contain actuators within a certain physical region of the network.

.. _`EPANET`: https://www.epa.gov/water-research/epanet
.. _`NumPy`: https://numpy.org/doc/2.1/reference/random/generated/numpy.random.normal.html
.. _`here`: https://man7.org/linux/man-pages/man8/tc-netem.8.html
.. _`documentation section`: experiment_config_docs#PLC Config Options
.. _`Per-PLC/Per-SCADA Config Options`: experiment_config_docs#Per-PLC/Per-SCADA Config Options
.. _`Examples`: examples.rst
.. _`attack`: attack_config_docs.rst
.. _`event`: event_config_docs.rst
