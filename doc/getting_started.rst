===============
Getting Started 
===============
To run an experiment with DHALSIM the following files are required:

* `EPANET Network .INP File`_
* DHALSIM Experiment Config File
* DHALSIM PLC Config File

While these are the required files to run a DHALSIM simulation, other configuration and data files can be included. However, because they are optional they will not be used in the Getting Started examples and instead one should refer to the `Config File Documentation`_ section for how and when to use them. These files include:

* Per Scada & Per PLC Configuration File
* Initial Tank Data .CSV file
* Demand Pattern .CSV File(s)
* Network Loss Data .CSV file
* Network Delay Data .CSV file 

**All example files can be found in the examples/getting_started folder from the root directory.**

#############
Basic Example
#############
For this example, the Minitown network will be used. This network consists of two pumps, PUMP1 and PUMP2, and one tank, TANK. The first thing to do is to create a DHALSIM experiment config file as follows. All DHALSIM config files end with the .YAML extension, a file format similar to JSON.

**example_config_1.yaml**

.. code-block:: yaml

   inp_file: minitown_map.inp
   plcs: !include minitown_plcs.yaml

Next, the :code:`minitown_plcs.yaml` file needs to be created. This file contains information about the PLCs in the network, including their name, attached actuators, and attached sensors. PLC groupings can be completely arbitrary, however typically PLCs are created based off the proximity between network elements of interest. 

**minitown_plcs.yaml**

.. code-block:: yaml

   - name: PLC1
     sensors:
       - TANK
   - name: PLC2
     actuators:
       - PUMP1
       - PUMP2 

These config files represents the minimum amount of information needed to run a DHALSIM experiemnt. It will run without any attacks or network events on a simple network topology, generating network traffic data between the two PLCs and SCADA system for a number of iterations equal to the number of hydraulic time steps.

######################
Output From Simulation
######################
All DHALSIM experiment runs output data generated from the hydraulic simulation and network emulation. Additionally, it also outputs the configuration options it recieved, allowing for an easy way to confirm the experimental parameters were as intended. 

First, the hydraulic simulation outputs two files, :code:`ground_truth.csv`, and :code:`scada_values.csv`. Only values at nodes specified as an actuator or sensor in the PLC config file are recorded at each iteration. Additionally, the status of each attacker is also recorded at each iteration. Table 1 details what values are saved for each element type in the network.

* :code:`ground_truth.csv` - This file contains the **actual** values resulting from the simulation, as opposed to any modified values as a result of some attack.
* :code:`scada_values.csv` - This file contains the the values that the SCADA sees. This means that if an attacker is performing a concealment or replay attack then the values in this file will be different from that in :code:`ground_truth.csv`.
.. list-table:: Table 1: Values Recorded for Each Network Element
   :widths: 25 25
   :header-rows: 1

   * - Network Element
     - Values Recorded
   * - Junction
     - Level (m)
   * - Tank
     - Level (m)
   * - Pump
     - Flowrate (m^3/s), Status (Open/Closed)
   * - Valve
     - Flowrate (m^3/s), Status (Open/Closed)
   * - Attacker
     - Attack Status (Attacking/Not Attacking)

Next, the network emulations outputs .PCAP files, which include the generated network traffic data. Network traffic data includes every packet sent during communication between the different PLCs, SCADA system, and attacker(s). These PCAP files are generated for each PLC, each attacker, the SCADA, and each router if the network topology type is complex (see `Config File Documentation`_ for more information on topology type.)

To analyze these PCAP files the program most often used is `Wireshark`_, however the PCAP files can also be read directly from code, such as using `Pyshark`_ for Python. The following are some additional resources that can helpful in understanding the results generated from the network emulation:

* `What is TCP (Transmission Control Protocol)?`_
* `ARP Protocol Packet Format`_
* `A Comprehensive Guide to ODVA CIP - Common Industrial Protocol`_

.. _`Config File Documentation`: https://github.com/tylertrimble/DHALSIM/blob/70aacea9d5c53556796e892785ba62a041bb4877/doc/config_docs
.. _`EPANET Network .INP File`: https://epanet22.readthedocs.io/en/latest/back_matter.html#input-file-format
.. _`Wireshark`: https://www.wireshark.org/
.. _`Pyshark`: https://github.com/KimiNewt/pyshark
.. _`What is TCP (Transmission Control Protocol)?`: https://www.geeksforgeeks.org/what-is-transmission-control-protocol-tcp/
.. _`ARP Protocol Packet Format`: https://www.geeksforgeeks.org/arp-protocol-packet-format/
.. _`A Comprehensive Guide to ODVA CIP - Common Industrial Protocol`: https://www.linkedin.com/pulse/comprehensive-guide-odva-cip-common-industrial-annamalai-tpwyc/
