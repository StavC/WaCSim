.. B.2 Input files and their roles
.. WaCSim User Manual

========================================
Input files and their roles
========================================

WaCSim needs a **main config file** (YAML) that you pass to ``wacsim``. That file references the hydraulic network (INP), the PLC layout (PLC YAML), and optionally attacks, events, and custom-algorithm configs. All paths in the main config are **relative to the directory containing the config file**.

----------------------------------------
Main config file (YAML)
----------------------------------------

This is the file you run: ``sudo wacsim <config>.yaml``. It is the **entry point** for the simulation.

**Required:**

- **``inp_file``** — Path to the EPANET INP file (e.g. ``EdenTown.inp``). Defines the water network and hydraulic settings.
- **``plcs``** — Path to the PLC definition file. You must use the ``!include`` directive, e.g. ``plcs: !include EdenTown_plc.yaml``.
- **``mode``** — ``plccontrol``, ``scadacontrol``, or ``hybridcontrol``. Default: ``plccontrol``. See :doc:`control_modes`.
- **``output_path``** — Folder where result CSVs and PCAPs are written. Default: ``output`` (relative to the config directory).
- **``iterations``** — Number of simulation time steps. If omitted, WaCSim uses the number of hydraulic time steps implied by the INP (duration ÷ hydraulic timestep).
- **``network_topology_type``** — ``simple`` (one shared network) or ``complex`` (each PLC and SCADA on their own subnet). Default: ``simple``. Affects where attackers sit and how realistic the network is.
- **``log_level``** — ``debug``, ``info``, ``warning``, ``error``, ``critical``. Default: ``info``.

**Optional (data and demand):**

- **``demand``** — ``pdd`` (pressure-driven demand) or ``dd`` (demand-driven). Default: ``pdd``.
- **``demand_patterns``** — Path to a CSV (or directory of CSVs for batch runs) with demand multipliers. Used when running with custom demand patterns.
- **``initial_tank_data``** — Path to a CSV of initial tank levels (e.g. for batch or scenario runs).
- **``network_loss_data``**, **``network_delay_data``**, **``network_jitter_data``** — Paths to CSVs defining loss/delay/jitter per link or time (see reference docs).

**Optional (attacks and events):**

- **``attacks``** — Path to a YAML file that defines device and/or network attacks, e.g. ``attacks: !include my_attacks.yaml``. See :doc:`attacks`.
- **``events``** — Path to a YAML file that defines network events (delay, loss), e.g. ``events: !include my_events.yaml``. See :doc:`events`.

**Optional (custom algorithms):**

- **``decision_maker_per_plc``** — Path to a YAML file that assigns per-actuator decision logic for each PLC (e.g. ``rule``, ``scada``, or a path to a Python script). See :doc:`custom_algorithms`.
- **``decision_maker_per_scadacommand``** — Path to a YAML file that assigns per-actuator decision logic for the SCADA (used in SCADA and hybrid modes).

All paths (``inp_file``, ``plcs``, ``output_path``, ``demand_patterns``, attack/event/decision-maker includes, etc.) are resolved **relative to the directory of the main config file**. Put the config in the same folder as the INP and PLC file (or use paths like ``subdir/EdenTown.inp``) so that WaCSim can find everything.

----------------------------------------
INP file (EPANET input)
----------------------------------------

The **INP file** is the standard EPANET input format. It defines:

- **Network layout** — Junctions, reservoirs, tanks, pipes, pumps, valves, and how they connect.
- **Demands** — Base demands and patterns (pattern IDs). WaCSim can override or supply demand via ``demand_patterns`` when using ``demand: pdd``.
- **Controls** — The ``[CONTROLS]`` section defines rule-based logic for pumps and valves (e.g. “open pump P1 if node T1 below 6”, “close valve V4 if node T2 above 10”). These are the **default** control rules. In WaCSim they can be overridden or supplemented by custom algorithms (see :doc:`custom_algorithms`).
- **Time settings** — ``[TIMES]``: duration, hydraulic timestep, report timestep. These determine the default simulation length if you do not set ``iterations`` in the main config.
- **Options** — Units, headloss model, demand model (e.g. PDA for pressure-driven), etc.

**What matters for WaCSim:**

- Every **sensor** and **actuator** you use in the PLC config must exist in the INP (by node or link ID). For example, if a PLC has sensor ``T1`` and actuator ``P1``, the INP must define a tank (or node) ``T1`` and a pump ``P1``.
- The ``[CONTROLS]`` section is used when an actuator is driven by **rule** (EPANET rules). Control rules often refer to a **dependent** node (e.g. tank level). WaCSim infers which sensors each PLC needs from these rules; you can also list them explicitly in the PLC config as ``dependent_sensors`` (or ``dependents`` in the decision-maker config).
- You can edit the INP in a text editor or in EPANET. See the EPANET documentation for the full format.

----------------------------------------
PLC config file (YAML)
----------------------------------------

The **PLC config** defines how many PLCs there are and which **sensors** and **actuators** each one has. It is included from the main config with ``plcs: !include <file>.yaml``.

**Structure:** a list of PLCs. Each PLC has:

- **``name``** — Unique PLC name (e.g. ``PLC1``, ``PLC2``). Used in logs, output filenames (e.g. ``PLC1_values.csv``), and as attack targets. Length typically 1–10 characters; alphanumeric and underscore only.
- **``sensors``** (optional) — List of node/link IDs that this PLC “owns” and reads directly from the hydraulic simulation (e.g. tank levels, junction pressures, valve flow). These IDs must exist in the INP. Examples: ``T1``, ``T2``, ``J5``, ``P1F`` (pump flow), ``V4F`` (valve flow).
- **``actuators``** (optional) — List of pump or valve IDs that this PLC controls. Each ID must exist in the INP. Examples: ``P1``, ``P2``, ``V4``, ``V5``.
- **``dependent_sensors``** (optional) — Alternative spelling: ``dependant_sensors``. List of sensor IDs this PLC needs from the network (e.g. from another PLC) to evaluate control rules. WaCSim can also infer these from the INP ``[CONTROLS]``; use this when you want to be explicit or when using custom algorithms with ``dependents``. The recommendation is to use ``dependents`` instead of ``dependent_sensors`` when using custom algorithms.

A PLC can have only sensors (e.g. a “sensing” PLC that sends tank level to others), only actuators (e.g. a PLC that only executes commands and gets dependent data from the network), or both. The combination defines who sends what over the network and who decides actuator state (depending on **mode** and decision-maker configs).

**Example (excerpt):**

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

Here PLC1 controls pump P2 (and will need dependent data, e.g. tank level, from another PLC or from the INP rules). PLC2 has sensors T1, V5F, J5 and controls valve V5.

----------------------------------------
Attack config file (optional)
----------------------------------------

If you set **``attacks: !include <file>.yaml``**, the included file must define one or both of:

- **``network_attacks``** — List of network attacks (DoS, Man-in-the-Middle, etc.). Each has ``name``, ``target`` (PLC name), ``trigger``, ``type``, and type-specific options.
- **``device_attacks``** — List of device-level attacks (if supported).

The file is usually a separate YAML in the same directory as the main config (or a subdirectory). See :doc:`attacks` for attack types and structure.

----------------------------------------
Event config file (optional)
----------------------------------------

If you set **``events: !include <file>.yaml``**, the included file defines **``network_events``**: a list of events that apply delay, packet loss, or jitter to specific links. Each event has a target (e.g. a PLC or SCADA link) and parameters. See :doc:`events` for details.

----------------------------------------
Decision-maker configs (optional)
----------------------------------------

- **``decision_maker_per_plc: !include <file>.yaml``** — For each PLC and actuator, specifies the decision logic: ``rule`` (use INP rules), ``scada`` (follow SCADA command), ``open``/``closed`` (fixed state), or a path to a Python file (custom algorithm). Optional **``dependents``** list for that actuator (sensors the algorithm needs).
- **``decision_maker_per_scadacommand: !include <file>.yaml``** — Same idea for the SCADA side: which actuators the SCADA decides and with which logic (rule, or path to Python). In hybrid mode, **``Hybrid_Values_To_Send``** can list sensor names (or derived values) the SCADA sends to PLCs in addition to the command.

If you omit these, WaCSim uses defaults: in PLC mode actuators use **rule** (INP); in SCADA mode they follow the SCADA’s rule-based decisions. See :doc:`custom_algorithms` for the full interface and where to put Python files.

----------------------------------------
Where to put files
----------------------------------------

- **Recommended:** Put the main config, INP, PLC YAML, and (if used) attack/event/decision-maker YAMLs in **one folder** (e.g. ``examples/GettingStartedEdenTown/``). Use relative paths in the config (e.g. ``EdenTown.inp``, ``EdenTown_plc.yaml``, ``output``). Then run ``sudo wacsim config.yaml`` from that folder.
- **Custom algorithms:** Python files can live in a subfolder (e.g. ``custom_algos/my_algo.py``). Reference them in the decision-maker YAML by path relative to the **main config file** (e.g. ``custom_algos/my_algo.py``).
- **Output:** Always written under ``output_path`` (relative to the config file directory). So if your config is in ``my_experiment/config.yaml`` and ``output_path: output``, results go to ``my_experiment/output/``.
