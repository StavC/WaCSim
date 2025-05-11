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

.. _`Config File Documentation`: https://github.com/tylertrimble/DHALSIM/blob/70aacea9d5c53556796e892785ba62a041bb4877/doc/config_docs
.. _`EPANET Network .INP File`: https://epanet22.readthedocs.io/en/latest/back_matter.html#input-file-format
.. _`Wireshark`: https://www.wireshark.org/
.. _`Pyshark`: https://github.com/KimiNewt/pyshark
.. _`What is TCP (Transmission Control Protocol)?`: https://www.geeksforgeeks.org/what-is-transmission-control-protocol-tcp/
.. _`ARP Protocol Packet Format`: https://www.geeksforgeeks.org/arp-protocol-packet-format/
.. _`A Comprehensive Guide to ODVA CIP - Common Industrial Protocol`: https://www.linkedin.com/pulse/comprehensive-guide-odva-cip-common-industrial-annamalai-tpwyc/
