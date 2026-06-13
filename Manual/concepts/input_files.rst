.. B.2 Input files and their roles
.. WaCSim User Manual

========================================
Input files and their roles
========================================

WaCSim needs a **main config file** (YAML) that you pass to ``wacsim``. That file references the hydraulic network (INP), the PLC layout (PLC YAML), and optionally attacks, events, custom-algorithm configs, and data CSVs for network conditions, sensor noise, demand patterns, and initial tank levels. All paths in the main config are **relative to the directory containing the config file**.

A complete set of realistic, in-depth demo files for every optional data input is provided in ``Manual/demo_files/``. This includes a comprehensive ``demo_config.yaml`` showing how to reference all parameters together, as well as CSV files configured with multiple PLCs and multiple simulation rows suitable for batch runs. Each demo file includes comments explaining its structure and values.


.. contents:: Table of Contents
   :depth: 2
   :local:


----------------------------------------
Main config file (YAML)
----------------------------------------

This is the file you run: ``sudo wacsim <config>.yaml``. It is the **entry point** for the simulation.

Below is a full example showing every available option. Only ``inp_file`` and ``plcs`` are strictly required; all others have defaults or are optional.

.. code-block:: yaml

   # === Required ===
   inp_file: MyNetwork.inp
   plcs: !include my_plcs.yaml

   # === Simulation settings (all optional) ===
   iterations: 500
   mode: plccontrol
   network_topology_type: complex
   output_path: output
   log_level: info
   mininet_cli: false
   demand: pdd
   saving_interval: 10
   batch_simulations: 1

   # === Data CSVs (all optional) ===
   initial_tank_data: initial_tanks.csv
   demand_patterns: demands.csv
   noise_scale_data: noise_scales.csv
   network_loss_data: losses.csv
   network_delay_data: delays.csv
   network_jitter_data: jitters.csv

   # === Sensor noise YAML config (optional, overrides noise_scale_data) ===
   sensor_noise: !include noise_config.yaml

   # === Attacks and events (all optional) ===
   attacks: !include my_attacks.yaml
   events: !include my_events.yaml

   # === Custom algorithms (all optional) ===
   decision_maker_per_plc: !include dm_plc.yaml
   decision_maker_per_scadacommand: !include dm_scada.yaml


Required parameters
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - ``inp_file``
     - Path (``.inp``)
     - Path to the EPANET INP file (e.g. ``MyNetwork.inp``). Defines the water distribution network: junctions, tanks, reservoirs, pipes, pumps, valves, demand patterns, control rules, and time settings. Can be edited in EPANET or any text editor.
   * - ``plcs``
     - ``!include`` path
     - Path to the PLC definition YAML (e.g. ``plcs: !include my_plcs.yaml``). Defines how many PLCs exist and which sensors/actuators each owns. See :ref:`plc-config` below.


Simulation settings
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 12 12 56

   * - Parameter
     - Type
     - Default
     - Description
   * - ``iterations``
     - Integer (> 0)
     - *from INP*
     - Number of simulation time steps. If omitted, WaCSim computes it from the INP file as ``duration ÷ hydraulic_timestep``. Setting a custom value changes the effective simulation duration but not the hydraulic timestep. For example, if the INP defines a 1-day simulation with 5-minute steps (288 steps), setting ``iterations: 100`` shortens the simulation to ~8.3 hours.
   * - ``mode``
     - String
     - ``plccontrol``
     - Control architecture: ``plccontrol``, ``scadacontrol``, or ``hybridcontrol``. Determines which entity's decision is applied to actuators. See :doc:`control_modes` for details.

       - **plccontrol** — Each PLC decides actuator state using its own local sensor cache. Network attacks on PLCs directly affect actuator behaviour.
       - **scadacontrol** — The SCADA decides actuator state using sensor data collected from all PLCs. Simple MitM attacks on a single PLC link may be thwarted because the SCADA has a global view.
       - **hybridcontrol** — Custom logic determines the decision source per actuator (PLC-side, SCADA-side, or a Python algorithm). This enables in-loop detection/response strategies.

   * - ``network_topology_type``
     - String
     - ``simple``
     - Cyber-network structure: ``simple`` or ``complex``.

       - **simple** — One shared network with a single router. All PLCs and the SCADA share two switches. An attacker can target all PLCs by spoofing one router.
       - **complex** — Each PLC and the SCADA are on individual subnets with their own routers. More realistic and recommended for MitM attack scenarios.

   * - ``output_path``
     - Path
     - ``output``
     - Folder where result CSVs and PCAPs are written. Must be a **relative** path from the config file directory (e.g. ``output``, ``results/run1``), not an absolute path.
   * - ``log_level``
     - String
     - ``info``
     - Controls terminal output verbosity. One of:

       - ``debug`` — All log events **and** print statements. Verbose.
       - ``info`` — Startup information and a progress bar with elapsed time, current iteration, and ETA.
       - ``warning`` — Warning-level events and above. Warnings usually don't affect results but may aid debugging.
       - ``error`` — Error-level events and above. Errors may indicate something went wrong but don't always halt the simulation.
       - ``critical`` — Only critical events that cause simulation shutdown (typically config file typos or missing files).

   * - ``mininet_cli``
     - Boolean
     - ``false``
     - If ``true``, the simulation pauses after network setup and opens the Mininet CLI for manual inspection. Type ``exit`` to resume. Useful for debugging network topology; not recommended for normal runs.
   * - ``demand``
     - String
     - ``pdd``
     - Demand model: ``pdd`` (pressure-driven demand) or ``dd`` (demand-driven).

       - **pdd** — Demand at each junction varies with pressure. Prevents unrealistic negative pressures. **Recommended for WaCSim** because attack scenarios often push the system into abnormal states where demand-driven analysis produces physically impossible results.
       - **dd** — Demand is always fully satisfied regardless of pressure. This is the EPANET default but can produce negative head values under attack conditions.

   * - ``saving_interval``
     - Integer (> 0)
     - ``0`` (disabled)
     - If non-zero, output CSV files are written incrementally every N iterations while the simulation is still running. PCAP files are always written in real time regardless of this setting. Useful for monitoring long simulations or for real-time analysis pipelines.
   * - ``batch_simulations``
     - Integer (> 0)
     - ``1``
     - Number of simulations to run sequentially with different initial conditions. Each simulation's output is saved to ``output_path/batch_<simulation_number>/``. When using batch mode, all data CSVs (initial tank levels, noise scales, network loss/delay/jitter) must have one row per simulation. See :ref:`batch-mode` for details.


.. _data-csvs:

Data CSV files
^^^^^^^^^^^^^^

All data CSVs follow a common structure:

- **Column headers** = names of PLCs (e.g. ``PLC1``, ``PLC2``), ``scada``, tank names (e.g. ``T1``, ``T2``), or demand pattern names — depending on the parameter.
- **Rows** = one row for a single simulation, or one row per simulation when using ``batch_simulations``.
- **File format** = ``.csv`` (comma-separated), readable by ``pandas.read_csv()``.

.. list-table::
   :header-rows: 1
   :widths: 22 15 63

   * - Parameter
     - Column headers
     - Description
   * - ``initial_tank_data``
     - Tank names
     - Initial tank levels in **meters**. Column headers must match tank IDs from the INP file. Each value overrides the INP's default initial level for that tank.
   * - ``demand_patterns``
     - Pattern names
     - Demand multipliers per timestep. Column headers must match demand pattern names from the INP file. Each row is one timestep's multiplier. For batch simulations, this should be a **folder** path containing numbered CSVs (``0.csv``, ``1.csv``, …).
   * - ``sensor_noise``
     - ``!include`` path
     - Per-PLC and per-sensor noise configuration (YAML). Supports five noise types. See :ref:`sensor-noise` for full details.
   * - ``noise_scale_data``
     - PLC names / ``scada``
     - *(Legacy)* Per-PLC Gaussian noise scale (CSV). See :ref:`sensor-noise` for full details. If both ``sensor_noise`` and ``noise_scale_data`` are present, ``sensor_noise`` takes priority.
   * - ``network_loss_data``
     - PLC names / ``scada``
     - Per-PLC/SCADA packet loss probability. See :ref:`network-loss`.
   * - ``network_delay_data``
     - PLC names / ``scada``
     - Per-PLC/SCADA network delay. See :ref:`network-delay`.
   * - ``network_jitter_data``
     - PLC names / ``scada``
     - Per-PLC/SCADA network jitter. See :ref:`network-jitter`.

Attacks, events, and custom algorithms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Parameter
     - Description
   * - ``attacks: !include <file>.yaml``
     - Defines device and/or network attacks. The included file must contain ``network_attacks`` and/or ``device_attacks`` lists. See :doc:`attacks`.
   * - ``events: !include <file>.yaml``
     - Defines network events (delay, packet loss, jitter applied to specific links at specific times). The included file must contain a ``network_events`` list. See :doc:`events`.
   * - ``decision_maker_per_plc: !include <file>.yaml``
     - Per-actuator decision logic for PLCs. Each actuator can use ``rule`` (INP rules), ``scada`` (follow SCADA), ``open``/``closed`` (fixed), or a path to a Python script. See :doc:`custom_algorithms`.
   * - ``decision_maker_per_scadacommand: !include <file>.yaml``
     - Per-actuator decision logic for the SCADA. Same options as above plus ``Hybrid_Values_To_Send`` for hybrid mode. See :doc:`custom_algorithms`.


----------------------------------------
INP file (EPANET input)
----------------------------------------

The **INP file** is the standard EPANET input format. It defines:

- **Network layout** — Junctions, reservoirs, tanks, pipes, pumps, valves, and how they connect.
- **Demands** — Base demands and patterns (pattern IDs). WaCSim can override or supply demand via ``demand_patterns`` when using ``demand: pdd``.
- **Controls** — The ``[CONTROLS]`` section defines rule-based logic for pumps and valves (e.g. "open pump P1 if node T1 below 6", "close valve V4 if node T2 above 10"). These are the **default** control rules. In WaCSim they can be overridden or supplemented by custom algorithms (see :doc:`custom_algorithms`).
- **Time settings** — ``[TIMES]``: duration, hydraulic timestep, report timestep. These determine the default simulation length if you do not set ``iterations`` in the main config.
- **Options** — Units, headloss model, demand model (e.g. PDA for pressure-driven), etc.

**What matters for WaCSim:**

- Every **sensor** and **actuator** you use in the PLC config must exist in the INP (by node or link ID). For example, if a PLC has sensor ``T1`` and actuator ``P1``, the INP must define a tank (or node) ``T1`` and a pump ``P1``.
- The ``[CONTROLS]`` section is used when an actuator is driven by **rule** (EPANET rules). Control rules often refer to a **dependent** node (e.g. tank level). WaCSim infers which sensors each PLC needs from these rules; you can also list them explicitly in the PLC config as ``dependent_sensors`` (or ``dependents`` in the decision-maker config).
- You can edit the INP in a text editor or in EPANET. See the EPANET documentation for the full format.


.. _plc-config:

----------------------------------------
PLC config file (YAML)
----------------------------------------

The **PLC config** defines how many PLCs there are and which **sensors** and **actuators** each one has. It is included from the main config with ``plcs: !include <file>.yaml``.

**Structure:** a list of PLCs. Each PLC has:

.. list-table::
   :header-rows: 1
   :widths: 25 12 63

   * - Field
     - Required
     - Description
   * - ``name``
     - Yes
     - Unique PLC name (1–10 characters, alphanumeric and underscore only, no spaces or hyphens). Used in logs, output filenames (e.g. ``PLC1_values.csv``), and as attack targets.
   * - ``sensors``
     - No
     - List of node/link IDs this PLC reads directly from the hydraulic simulation. IDs must exist in the INP. For **tanks and junctions**: the sensor reads level/head in meters. For **pumps and valves**: append ``F`` to the name (e.g. ``P1F``, ``V4F``) to read flow in the INP's flow units.
   * - ``actuators``
     - No
     - List of pump or valve IDs this PLC controls. Each ID must exist in the INP.
   * - ``dependent_sensors``
     - No
     - Sensors this PLC needs from **other** PLCs over the network (e.g. a tank level needed to evaluate a control rule). WaCSim auto-infers these from INP ``[CONTROLS]``; use this to be explicit or to add extra sensors for custom algorithms. Alternative spelling: ``dependant_sensors`` (pick one, not both).

A PLC can have only sensors, only actuators, or both. The combination defines who sends what over the network and who decides actuator state.

**Example:**

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

Here PLC1 controls pump P2 (and will need dependent data from another PLC). PLC2 has sensors T1, V5F, J5 and controls valve V5.


----------------------------------------
Attack config file (optional)
----------------------------------------

If you set **``attacks: !include <file>.yaml``**, the included file must define one or both of:

- **``network_attacks``** — List of network attacks (DoS, Man-in-the-Middle, etc.). Each has ``name``, ``target`` (PLC name), ``trigger``, ``type``, and type-specific options.
- **``device_attacks``** — List of device-level attacks (if supported).

See :doc:`attacks` for attack types and structure.


----------------------------------------
Event config file (optional)
----------------------------------------

If you set **``events: !include <file>.yaml``**, the included file defines **``network_events``**: a list of events that apply delay, packet loss, or jitter to specific links at specific times. See :doc:`events` for details.


----------------------------------------
Decision-maker configs (optional)
----------------------------------------

- **``decision_maker_per_plc: !include <file>.yaml``** — For each PLC and actuator, specifies the decision logic: ``rule`` (use INP rules), ``scada`` (follow SCADA command), ``open``/``closed`` (fixed state), or a path to a Python file (custom algorithm). Optional **``dependents``** list for that actuator (sensors the algorithm needs).
- **``decision_maker_per_scadacommand: !include <file>.yaml``** — Same idea for the SCADA side: which actuators the SCADA decides and with which logic (rule, or path to Python). In hybrid mode, **``Hybrid_Values_To_Send``** can list sensor names (or derived values) the SCADA sends to PLCs in addition to the command.

If you omit these, WaCSim uses defaults: in PLC mode actuators use **rule** (INP); in SCADA mode they follow the SCADA's rule-based decisions. See :doc:`custom_algorithms` for the full interface and where to put Python files.


----------------------------------------
Where to put files
----------------------------------------

- **Recommended:** Put the main config, INP, PLC YAML, and (if used) attack/event/decision-maker YAMLs in **one folder** (e.g. ``examples/GettingStartedEdenTown/``). Use relative paths in the config (e.g. ``EdenTown.inp``, ``EdenTown_plc.yaml``, ``output``). Then run ``sudo wacsim config.yaml`` from that folder.
- **Custom algorithms:** Python files can live in a subfolder (e.g. ``custom_algos/my_algo.py``). Reference them in the decision-maker YAML by path relative to the **main config file** (e.g. ``custom_algos/my_algo.py``).
- **Output:** Always written under ``output_path`` (relative to the config file directory). So if your config is in ``my_experiment/config.yaml`` and ``output_path: output``, results go to ``my_experiment/output/``.
- **Data CSVs:** Place them in the same folder as the config file and reference by filename (e.g. ``noise_scale_data: noise_scales.csv``).


.. _sensor-noise:

========================================
Sensor noise
========================================

WaCSim can add **configurable noise** to sensor readings, independently per PLC and even per individual sensor. This is useful for modelling realistic sensor measurement variability, testing the robustness of detection and control algorithms under noisy conditions, or simulating malfunctioning / degrading sensors.

- **Actuator values are NOT affected** — only sensor readings are perturbed.
- Noise is applied every iteration, with a fresh random sample each time.

There are **two ways** to configure sensor noise:

1. **``sensor_noise`` (YAML)** — the primary, more powerful approach. Supports five noise types and per-sensor overrides.
2. **``noise_scale_data`` (CSV)** — the legacy approach. Supports Gaussian (multiplicative) noise only, with a single scale per PLC.

If **both** are present in the config, ``sensor_noise`` takes priority.


Noise types
^^^^^^^^^^^

WaCSim supports five noise types. In the table below, *value* is the true sensor reading, *scale* is the configured scale factor, and *iteration* is the current simulation step index.

.. list-table::
   :header-rows: 1
   :widths: 20 35 45

   * - Type
     - Formula
     - Use case
   * - ``gaussian``
     - ``value + N(0, scale × value)``
     - Standard measurement noise (multiplicative). Std-dev scales with reading magnitude — mirrors real sensor behaviour.
   * - ``gaussian_absolute``
     - ``value + N(0, scale)``
     - Fixed standard deviation regardless of reading magnitude (e.g. ±0.1 bar transducer accuracy).
   * - ``uniform``
     - ``value + U(-scale × value, +scale × value)``
     - Bounded random noise. Useful for worst-case analysis where extreme values are as likely as small ones.
   * - ``percentage``
     - ``value × (1 + U(-scale, +scale))``
     - Fixed percentage accuracy band (e.g. ±3% of reading).
   * - ``drift``
     - ``value + scale × iteration``
     - Deterministic sensor degradation / slowly increasing bias. Models sensors that lose calibration over time.


``sensor_noise`` — YAML config (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``sensor_noise`` option accepts a YAML file via ``!include``. The file defines a list of PLCs, each with optional per-sensor overrides.

**Main config:**

.. code-block:: yaml

   sensor_noise: !include noise_config.yaml

**noise_config.yaml** (see ``Manual/demo_files/demo_sensor_noise.yaml``):

.. code-block:: yaml

   - name: PLC1
     default_noise: gaussian
     default_scale: 0.05
     sensors:
       - name: T1
         noise_type: uniform
         scale: 0.03
       - name: J5
         noise_type: gaussian_absolute
         scale: 0.1

   - name: PLC2
     default_noise: gaussian
     default_scale: 0.08

**Fields:**

.. list-table::
   :header-rows: 1
   :widths: 25 12 63

   * - Field
     - Required
     - Description
   * - ``name``
     - Yes
     - PLC name (must match a PLC in the PLC config).
   * - ``default_noise``
     - No
     - Default noise type for all sensors on this PLC. One of: ``gaussian``, ``gaussian_absolute``, ``uniform``, ``percentage``, ``drift``. Defaults to ``gaussian``.
   * - ``default_scale``
     - No
     - Default scale value for all sensors on this PLC. Defaults to ``0`` (no noise).
   * - ``sensors``
     - No
     - List of per-sensor overrides. Each entry has ``name`` (sensor ID), ``noise_type``, and ``scale``. Sensors not listed use the PLC defaults.

In the example above:

- PLC1's sensor **T1** uses *uniform* noise with scale 0.03, sensor **J5** uses *gaussian_absolute* with scale 0.1, and all other PLC1 sensors use *gaussian* with scale 0.05.
- PLC2's sensors all use *gaussian* noise with scale 0.08 (no per-sensor overrides).
- Any PLC not listed in the file gets **no noise** (scale = 0).


``noise_scale_data`` — CSV (legacy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The legacy ``noise_scale_data`` CSV configures a single Gaussian (multiplicative) noise scale per PLC. This is equivalent to setting ``default_noise: gaussian`` and ``default_scale: <value>`` for every PLC in the YAML approach.

**How it works:**

.. code-block:: text

   noisy_value = sensor_value + np.random.normal(0, noise_scale × sensor_value)

The noise is **multiplicative**: the standard deviation of the Gaussian distribution equals ``noise_scale × sensor_value``. This means larger readings receive proportionally larger noise, which mirrors real-world sensor behaviour where measurement error often scales with the magnitude. The function used is NumPy's ``np.random.normal``.

- A ``noise_scale`` of ``0`` (or omitting the PLC from the CSV) disables noise for that PLC.

**CSV format** (see ``Manual/demo_files/demo_noise_scale_data.csv``):

.. code-block:: text

   PLC1,PLC2,scada
   0.05,0.10,0.02

This gives PLC1 a 5% noise scale (std = 0.05 × value), PLC2 a 10% noise scale, and SCADA a 2% noise scale.

For batch simulations, add one row per simulation (see ``Manual/demo_files/demo_noise_scale_batch.csv``):

.. code-block:: text

   PLC1,PLC2,scada
   0.02,0.05,0.01
   0.05,0.10,0.03
   0.10,0.15,0.05


Backward compatibility
^^^^^^^^^^^^^^^^^^^^^^^

The ``noise_scale_data`` CSV continues to work unchanged and defaults to Gaussian (multiplicative) noise. If both ``sensor_noise`` and ``noise_scale_data`` are present in the config, ``sensor_noise`` takes priority and ``noise_scale_data`` is ignored.


**When to use sensor noise:**

- **Realism:** Real sensors have measurement uncertainty. Adding noise makes the simulation more representative of field conditions.
- **Algorithm robustness:** Test whether detection algorithms (e.g. anomaly detectors, CUSUM) or custom control algorithms can tolerate noisy inputs without false alarms or degraded performance.
- **Batch sweeps:** Combine with ``batch_simulations`` to systematically vary noise levels across runs and study sensitivity.
- **Sensor degradation:** Use ``drift`` noise to model sensors that lose calibration over time and study long-term system behaviour.


.. _network-loss:

========================================
Network packet loss (network_loss_data)
========================================

Network losses model situations where packets are sent but not received. Packets can be lost for a variety of reasons; configuring loss allows you to represent non-ideal communication conditions.

**How it works:**

Each value in the CSV represents the **probability (0–100%)** that a given packet on that PLC's or SCADA's link is dropped. This is implemented via Mininet using Linux's ``tc``/``netem`` module.

**CSV format** (see ``Manual/demo_files/demo_network_loss_data.csv``):

.. code-block:: text

   PLC1,PLC2,scada
   1.5,2.0,0.5

Here PLC1's link has a 1.5% loss probability, PLC2 has 2%, and SCADA has 0.5%.

For batch simulations, add one row per simulation.


.. _network-delay:

========================================
Network delay (network_delay_data)
========================================

Network delays model the constant latency of packet transmission across a physical distance. All real networks have some inherent delay.

**How it works:**

Each value represents a **constant delay in milliseconds** applied to every packet on that link. Implemented via Mininet/``tc``-``netem``. The parser automatically appends ``ms`` to each value.

**CSV format** (see ``Manual/demo_files/demo_network_delay_data.csv``):

.. code-block:: text

   PLC1,PLC2,scada
   10.0,15.0,5.0

Here PLC1's link has a 10 ms delay, PLC2 has 15 ms, and SCADA has 5 ms.

For batch simulations, add one row per simulation.


.. _network-jitter:

========================================
Network jitter (network_jitter_data)
========================================

Network jitter adds **random additional delay** drawn from a normal distribution, on top of any constant delay. This models the variability in real-world packet transmission times.

**How it works:**

Each value represents the **standard deviation (in milliseconds)** of the additional random delay. For example, a jitter value of ``5.0`` adds a random delay sampled from a normal distribution with mean 0 and std 5 ms to each packet. Implemented via Mininet/``tc``-``netem``.

**CSV format** (see ``Manual/demo_files/demo_network_jitter_data.csv``):

.. code-block:: text

   PLC1,PLC2,scada
   3.0,5.0,2.0

For batch simulations, add one row per simulation.


.. _initial-tanks:

========================================
Initial tank levels (initial_tank_data)
========================================

Override the default initial tank levels from the INP file. This is particularly useful for batch simulations where you want to test different starting conditions.

**CSV format** (see ``Manual/demo_files/demo_initial_tank_data.csv``):

.. code-block:: text

   T1,T2
   4.5,3.2

Column headers must match tank IDs from the INP file exactly. Each value is the initial level in **meters**.

For batch simulations, add one row per simulation:

.. code-block:: text

   T1,T2
   4.5,3.2
   5.0,4.0
   3.8,2.5


.. _demand-patterns:

========================================
Demand patterns (demand_patterns)
========================================

Provide custom demand multipliers that override or supplement the patterns defined in the INP file.

**Single simulation — CSV format** (see ``Manual/demo_files/demo_demand_patterns.csv``):

.. code-block:: text

   pattern1,pattern2
   0.5,0.6
   0.8,0.9
   1.2,1.1
   1.0,1.0
   0.7,0.8
   0.4,0.5

Column headers must match demand pattern names from the INP. Each row is one timestep's multiplier.

**Batch simulations — folder of CSVs:**

When running batch simulations, ``demand_patterns`` should point to a **folder** containing numbered CSVs: ``0.csv``, ``1.csv``, ``2.csv``, etc. Each CSV has the same column format as above. The file number corresponds to the simulation index.

.. code-block:: yaml

   batch_simulations: 3
   demand_patterns: demand_folder/

Where ``demand_folder/`` contains ``0.csv``, ``1.csv``, ``2.csv``.


.. _batch-mode:

========================================
Batch simulations
========================================

Setting ``batch_simulations`` to a value greater than 1 runs multiple sequential simulations with different initial conditions. Each simulation picks a different row from the data CSVs:

- Row 0 → simulation 0
- Row 1 → simulation 1
- ...and so on.

**Requirements:**

- All data CSVs (``initial_tank_data``, ``noise_scale_data``, ``network_loss_data``, ``network_delay_data``, ``network_jitter_data``) must have **at least** as many rows as ``batch_simulations``.
- ``demand_patterns`` should be a folder with one numbered CSV per simulation (see :ref:`demand-patterns`).
- Output for each simulation is saved to ``output_path/batch_<simulation_number>/``.

**Example config:**

.. code-block:: yaml

   batch_simulations: 3
   initial_tank_data: initial_tanks_batch.csv
   noise_scale_data: noise_batch.csv
   demand_patterns: demands/
   output_path: output
