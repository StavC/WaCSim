.. Part A: Quick Start — Installing and Running Your First Example
.. WaCSim User Manual

========================================
Part A: Quick Start
========================================

This section gets you from zero to a successful WaCSim run: install the software, then run a minimal example and see where the results go.

----------------------------------------
What you need
----------------------------------------

- **Linux** — WaCSim uses Mininet and Linux networking (e.g. ``tcpdump``). It is intended to run on a native Linux machine or inside a Linux virtual machine (e.g. Ubuntu on VirtualBox or VMware).
- **sudo** — The simulator creates virtual network interfaces and runs network tools; you must run the ``wacsim`` command with ``sudo``.
- **Python 3** — The codebase targets Python 3 (3.8+). The install script uses ``python3`` and ``pip``.

----------------------------------------
Installation (summary)
----------------------------------------

1. **Clone the WaCSim repository** and go into its root directory:

   .. code-block:: bash

      git clone <WaCSim-repository-URL>
      cd WaCSim-master

   

2. **Run the install script** from the repository root:

   .. code-block:: bash

      ./install.sh

   The script will:

   - Update ``apt`` and install system packages (e.g. ``git``, ``python3``, ``python3-pip``, ``curl``).
   - Install **MiniCPS** and **cpppo** (Ethernet/IP emulation).
   - Clone and install **DHALSIM-epynet** (EPANET wrapper).
   - Clone and install **Mininet** from source (network emulation).
   - Install **netfilterqueue** and **python-netfilterqueue** (used for some attacks).
   - Install WaCSim itself in editable mode (``pip install -e .``).

   **Optional:** To also install documentation build dependencies, run:

   .. code-block:: bash

      ./install.sh -d

   When installation finishes, the script prints that you can run WaCSim with ``sudo wacsim your_config.yaml``.

3. **Check that the command is available:**

   .. code-block:: bash

      which wacsim
      sudo wacsim --help

   You should see the path to the ``wacsim`` script and the help message for the config file and optional ``-o`` output folder.


----------------------------------------
Running your first example
----------------------------------------

WaCSim is driven by a **main config file** (YAML). That file points to:

- An **EPANET INP file** (the water network),
- A **PLC config file** (which PLCs exist and which sensors/actuators they use).

The recommended first example is in **``examples/GettingStartedEdenTown/``**. It uses the **EdenTown** network: two reservoirs (R1, R2), two tanks (T1, T2), two pumps (P1, P2), three valves (V1, V4, V5), and four PLCs. Control is **PLC mode** only — no attacks, no custom algorithms. All pump and valve logic comes from the EPANET ``[CONTROLS]`` rules in the INP file.

**Step 1 — Go to the example directory**

From the WaCSim repository root:

.. code-block:: bash

   cd examples/GettingStartedEdenTown

**Step 2 — Run WaCSim**

.. code-block:: bash

   sudo wacsim config.yaml

You can also pass a path to the config file from anywhere, for example:

.. code-block:: bash

   sudo wacsim /path/to/WaCSim-master/examples/GettingStartedEdenTown/config.yaml

WaCSim will:

- Parse the config and the included PLC file (``EdenTown_plc.yaml``).
- Resolve paths to the INP file (``EdenTown.inp``) and demand pattern (``demands_EdenTown.csv``) relative to the config file directory.
- Run the hydraulic simulation (EPANET) and the cyber simulation (Mininet, PLCs, SCADA) for the number of iterations set in the config (100 in this example).
- Print progress (and any warnings/errors) to the terminal.

**Step 3 — Where the output goes**

The config sets **``output_path: output``**, so results are written to **``output``** in the **same directory as the config file**. After running from ``examples/GettingStartedEdenTown``, you will see:

.. code-block:: text

   examples/GettingStartedEdenTown/output/

That folder will contain (among other files):

- **``ground_truth.csv``** — Actual hydraulic state at each time step (tank levels, pump/valve status, etc.).
- **``scada_values.csv``** — Values the SCADA system received (no attacks in this example, so they match the ground truth).
- **``PLC1_values.csv``** … **``PLC4_values.csv``** — Values each PLC recorded.
- **``*.pcap``** — Network traffic (e.g. ``scada-eth0.pcap``, ``PLC1-eth0.pcap``, …).

**Step 4 — Check that it worked**

Open the ground truth CSV (e.g. in a text editor or spreadsheet). You should see:

- A column for iteration/time.
- Columns for the elements defined in the INP and PLC config (e.g. T1, T2 levels; P1, P2 status; V4, V5 status).

If those files are present and contain data, your first run was successful.

----------------------------------------
What’s in the example config files?
----------------------------------------

**``config.yaml``** (main config):

.. code-block:: yaml

   inp_file: EdenTown.inp
   plcs: !include EdenTown_plc.yaml
   mode: plccontrol
   output_path: output
   iterations: 100
   network_topology_type: simple
   demand: pdd
   demand_patterns: demands_EdenTown.csv
   log_level: info

- **``inp_file``** — The EPANET input file (network layout, controls, duration, time step). Path is relative to the config file directory.
- **``plcs: !include EdenTown_plc.yaml``** — Includes the PLC definition file. The ``!include`` directive is required for included YAML files.
- **``mode: plccontrol``** — PLCs decide actuator states from EPANET rules and from sensor data they receive over the network; SCADA only monitors.
- **``output_path``** — Where result CSVs and PCAPs are written (relative to the config directory).
- **``iterations``** — Number of simulation steps (100 here; the INP defines a 24 h run with 5 min steps if you use the full duration).
- **``demand_patterns``** — CSV of demand multipliers used when ``demand: pdd`` (pressure-driven demand).

**``EdenTown_plc.yaml``** (PLC definition):

.. code-block:: yaml

   - name: PLC1
     actuators:
       - P2
   - name: PLC2
     sensors:
       - T1
       - V5F
       - J5
     actuators:
       - V5
   - name: PLC3
     sensors:
       - T2
       - V4F
       - J4
     actuators:
       - V4
   - name: PLC4
     actuators:
       - P1
     sensors:
       - J1
       - P1F
       - V1F

- **PLC1** — Controls pump **P2**. The INP rules say P2 opens when tank T2 is below 3 m and closes when above 7 m; PLC1 gets T2 from PLC3 over the network.
- **PLC2** — Has sensors T1, V5F, J5; controls valve **V5** (based on T1 level from the INP rules).
- **PLC3** — Has sensors T2, V4F, J4; controls valve **V4** (based on T2 level).
- **PLC4** — Controls pump **P1** (INP: open when T1 below 6 m, close when above 7 m); has local sensors J1, P1F, V1F. T1 comes from PLC2 over the network.

This is a **vanilla** setup: no ``attacks``, no ``decision_maker_per_plc``. All behavior comes from the INP ``[CONTROLS]`` and PLC-to-PLC data exchange. For SCADA or hybrid mode, or to add attacks or custom algorithms, see the **Concepts** and **Tutorials** sections.

----------------------------------------
Next steps
----------------------------------------

- **Concepts (Part B)** — How WaCSim works: control modes (PLC / SCADA / Hybrid), input files, attacks, events, custom algorithms, and output files.
- **Tutorials (Part C)** — Change the run length, add a DoS attack, or add a custom algorithm.
- **Reference** — Full list of main config options (e.g. ``output_path``, ``mode``, ``iterations``), attack and event configs, and custom algorithm interface.

----------------------------------------
