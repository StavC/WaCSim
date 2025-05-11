# Water Computer Simulation (WaCSim)
An open-source digital twin for water distribution systems, built upon [DHALSIM](https://github.com/Critical-Infrastructure-Systems-Lab/DHALSIM) with extended capabilities.

WaCSim utilizes multiple open-source tools to simulate both the hydraulic and cyber layer of the simulation. For the hydraulic layer, WaCSim relies upon EPANET, an open-source hydraulic solver for water distribution systems. EPANET is available with two simulators, [WNTR](https://github.com/USEPA/WNTR) and [epynet](https://github.com/Vitens/epynet). For the cyber layer, WaCSim relies upon both [mininet](https://github.com/mininet/mininet) and [miniCPS](https://github.com/scy-phy/minicps) to simulate the common industrial system and the overall network communication between SCADA and PLCs.  

## Features
WaCSim is a highly customizable digital twin. The following are some capabilities of WaCSim:
1. Customizable network architecture, with the ability to control the actuators, sensors, and dependent sensors for each PLC and for any water distribution system. 
2. Complex PLC and SCADA behavior via user-made scripts.
3. A variety of attack types such as various Man in the Middle variants and denial of service. Each attack is detailed in the [Attack Config Options](doc/attack_config_docs.rst) section of the documentation.
4. Ability to simulate network losses, delays, jitters, and sensor noise for each PLC and SCADA.
5. Many more configuration options, detailed in the [Experiment Config Options](doc/experiment_config_docs.rst) section of the documentation.
## Installation

Installing WaCSim requires either access to a Linux machine or the installation of a virtual machine. Installation, including with a virtual machine, is covered in detail on the [Installation](doc/installation.rst) docs page.

## Running

Any WacSim config file can be run by opening up a terminal in the folder the config file is located in and running ```sudo wacsim <config name>.yaml```. Additionally, one can also provide an absolute or relative path to the config file. More information on how to get started with WaCSim is provided in the [Getting Started](doc/getting_started.rst) docs page.
