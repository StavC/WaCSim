.. B.8 Execution flow
.. WaCSim User Manual

========================================
Execution flow
========================================

This section outlines what happens when you run ``sudo wacsim config.yaml``, from config parsing to the end of the simulation.

----------------------------------------
1. Command and config parsing
----------------------------------------

- You run **``sudo wacsim <config>.yaml``** (optionally with ``-o <output_folder>``)
- **ConfigParser** loads and validates the main config (INP path, PLCs, mode, iterations, attacks, events, decision makers, etc.). Paths are resolved relative to the **directory containing the config file**.
- An **intermediate YAML** is generated: it merges the main config with data derived from the INP file (controls, actuators, times, initial tank values) and from any included files (attacks, events, decision makers). This intermediate YAML is the single source of truth for the rest of the run.
- A **SQLite database** is created (or reset) and initialized with initial tank levels, actuator states, and tag layout. The **physical process** and all **cyber processes** (PLCs, SCADA, attackers, events) use this database to read and write sensor/actuator values.

----------------------------------------
2. File copy and Mininet startup
----------------------------------------

- **InputFilesCopier** copies the config, INP, PLC YAML, attack/event/decision-maker files, and any CSV data (e.g. demand patterns, network loss/delay) into a **configuration** folder so that Mininet nodes can access them (paths in the intermediate YAML point to these copies where needed).
- **Mininet** is started and the topology is built (simple or complex): hosts for each PLC, SCADA, routers, switches, and attacker/event nodes as defined in the intermediate YAML.
- **Router** processes are started (one per PLC gateway and for the SCADA gateway) to forward traffic and capture PCAPs.

----------------------------------------
3. Process launch
----------------------------------------

The following processes are started (order may vary; all run in parallel after launch):

- **Plant (physical process)** — Runs the hydraulic simulator (EPANET/WNTR). Reads actuator state from the database, advances the hydraulic model one time step, writes sensor and actuator state to the database, and writes **ground_truth.csv**.
- **PLCs** — One process per PLC. Each PLC runs a main loop: wait for sync, read from database and network (dependent sensors, SCADA commands in SCADA/hybrid mode), run control logic (INP rules or custom algorithms), write actuator commands to the database, send its data to the SCADA (and in complex topology to routers), write **<PLC>_values.csv** and optionally a PCAP.
- **SCADA** — One process. Collects sensor/actuator data from all PLCs over the network, runs control logic in SCADA/hybrid mode (rules or custom algorithms), writes ScadaCommand_* values to the database and sends them to PLCs, writes **scada_values.csv** and **scada-eth0.pcap**.
- **Attackers** (if configured) — One process per network attack. Each performs ARP poisoning (or equivalent) and then runs the attack logic (e.g. drop packets, modify values) on the traffic to/from the target PLC. PCAPs are written per attacker interface.
- **Network events** (if configured) — One process per event. Each applies **tc** (traffic control) on the relevant link to introduce delay and/or packet loss when the event’s trigger is active.

----------------------------------------
4. Iteration loop (synchronized)
----------------------------------------

Simulation time is divided into **iterations** (set by ``iterations`` in the config or derived from the INP).

- The **plant** drives the loop: it waits for the cyber layer to be ready, then runs one **hydraulic step**, updates the database with the new sensor and actuator state, and writes a row to **ground_truth.csv**. It then sets a sync flag so that PLCs and SCADA can proceed.
- **PLCs** and **SCADA** wait for the sync flag, then **read** the latest state from the database (and, over the network, dependent sensors and SCADA commands). They run their control logic (rules or ``AlgoRun``), **write** actuator commands (and SCADA commands) back to the database, and update their CSV output. Then they set their sync flags so the plant can advance.
- **Attackers** and **events** act on the network during the cyber phase (drop, delay, or modify packets). They do not drive the loop; they only affect what PLCs and SCADA receive.
- This cycle repeats until the number of iterations is reached.

----------------------------------------
5. Shutdown and output
----------------------------------------

- When the plant has finished the last iteration, it exits. The runner **polls** all processes; when the plant exits, it triggers shutdown of the others (PLCs, SCADA, attackers, events, routers).
- All CSV and PCAP files have already been written incrementally during the run (or at the end, depending on the component). The **output_path** directory contains **ground_truth.csv**, **scada_values.csv**, **PLC*_values.csv**, and **\*.pcap** (and optionally **water_loss.csv**, **demand_deficit.csv**, and a **configuration/** copy).
- Mininet is torn down. The run is complete.

----------------------------------------
Summary
----------------------------------------

**Config** → **Parse & validate** → **Intermediate YAML + DB** → **Copy files** → **Start Mininet** → **Start plant, PLCs, SCADA, attackers, events** → **Iteration loop (hydraulic step → DB update → cyber read/decide/write → sync)** → **Shutdown** → **Output in output_path**.

See :doc:`overview` for the role of the database and :doc:`output_files` for what each output file contains.
