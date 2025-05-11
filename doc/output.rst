=================
Simulation Output
=================
All WaCSim experiments run output data generated from the hydraulic simulation and network emulation. Additionally, it also outputs the configuration options it received, allowing 
for an easy way to confirm the experimental parameters were as intended. 

First, the hydraulic simulation outputs two files, :code:`ground_truth.csv`, and :code:`scada_values.csv`. Only values at nodes specified as an actuator or sensor
in the PLC config file are recorded at each iteration. Additionally, the status of each attacker is also recorded at each iteration. Table 1 details what values 
are saved for each element type in the network.

Next, the network emulation outputs .PCAP files, which include the generated network traffic data. Network traffic data includes every packet sent during 
communication between the different PLCs, SCADA system, and attacker(s). These PCAP files are generated for each PLC, each attacker, the SCADA, and each router if 
the network topology type is complex (see `Config Documentation`_ for more information on topology type.)

* :code:`ground_truth.csv` - This file contains the **actual** values resulting from the simulation, as opposed to any modified values as a result of some attack.
* :code:`<PLC name>_values.csv` - These files contain the values that each PLC sees. Typically, this includes the sensors and actuators directly connected to the PLC, and dependent sensors based on the control rules defined in the .INP file.
* :code:`scada_values.csv` - This file contains the values that the SCADA sees. This means that if an attacker is performing a concealment or replay attack then the values in this file will be different from that in :code:`ground_truth.csv`.
* :code:`<PLC name>-eth0.pcap` - These files contain the network traffic that involved a specific PLC. This traffic occurs between other PLCS, the SCADA system, and an attacker if being attacked.
* :code:`scada-eth0.pcap` - This file contains the network traffic related to SCADA sending or requesting data from PLCs, or an attacker if being attacked.
* :code:`<Router name>-eth0.pcap` - These files contain the network traffic that passes through each router. In a complex topology, each PLC has it's own router. Not present for simple network topology.
* :code:`<attack name>-etho0.pcap` - These files contain all the network traffic that goes to and from attackers.
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



To analyze PCAP files the program most often used is `Wireshark`_, however the PCAP files can also be read directly from code, such as using `Pyshark`_ for Python. The following are some additional resources that can be helpful in understanding the results generated from the network emulation:

* `What is TCP (Transmission Control Protocol)?`_
* `ARP Protocol Packet Format`_
* `A Comprehensive Guide to ODVA CIP - Common Industrial Protocol`_

.. _`Wireshark`: https://www.wireshark.org/
.. _`Pyshark`: https://github.com/KimiNewt/pyshark
.. _`What is TCP (Transmission Control Protocol)?`: https://www.geeksforgeeks.org/what-is-transmission-control-protocol-tcp/
.. _`ARP Protocol Packet Format`: https://www.geeksforgeeks.org/arp-protocol-packet-format/
.. _`A Comprehensive Guide to ODVA CIP - Common Industrial Protocol`: https://www.linkedin.com/pulse/comprehensive-guide-odva-cip-common-industrial-annamalai-tpwyc/
.. _`Config Documentation`: doc/config_docs.rst
