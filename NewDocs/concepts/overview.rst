.. B.1 What WaCSim does (high level)
.. WaCSim User Manual

========================================
What WaCSim does
========================================

WaCSim (Water and Cyber Simulation) is a **cyber–physical digital twin** for water distribution systems (WDSs). It simulates both the **physical behavior** of the network (hydraulics) and the **cyber layer** (communication and control) in a single, synchronized environment. That lets you study how control decisions, network traffic, and cyber-attacks affect the water system, and how the water system responds.

----------------------------------------
Two layers, one simulation
----------------------------------------

**Hydraulic layer**
  WaCSim uses **EPANET** (via an internal wrapper) to simulate the water network: pipes, junctions, tanks, reservoirs, pumps, valves, demands, and pressures. At each time step, EPANET advances the hydraulic state (tank levels, flows, pressures) and reports sensor values (e.g. tank level, pump flow, valve status). Actuators (pumps, valves) are driven by **commands** that come from the cyber layer, not only from EPANET’s built-in control rules.

**Cyber layer**
  WaCSim uses **Mininet** to emulate a network of devices and **MiniCPS** (with Ethernet/IP) to emulate industrial control traffic. On this network run:

  - **PLCs** — One process per PLC. Each PLC is attached to a subset of sensors and actuators defined in your config. It reads sensor values (from a shared database that the hydraulic side updates), may receive data from other PLCs or from the SCADA over the network, runs control logic (EPANET rules or your custom algorithms), and writes actuator commands back to the database.

  - **SCADA** — One central process. It collects sensor data from all PLCs over the network and, depending on the **control mode**, either only records them (PLC mode) or decides actuator commands and sends them to the PLCs (SCADA or hybrid mode).

  - **Attackers** (optional) — Processes that intercept, drop, or modify traffic between PLCs and SCADA (e.g. denial of service, man-in-the-middle).

  - **Network events** (optional) — Simulated delay or packet loss on links.

So: the **hydraulic simulator** and the **cyber processes** (PLCs, SCADA, attackers) all run at the same time. They are synchronized step-by-step.

----------------------------------------
Step-by-step coupling
----------------------------------------

Simulation time is divided into **iterations** (time steps). The number of iterations is set in your config (e.g. ``iterations: 100``) or defaults to the number of hydraulic time steps in the INP file.

At each iteration, roughly:

1. **Hydraulic step** — The plant (physical process) runs EPANET for one time step. Sensor values (tank levels, junction pressures, pump flows, valve status, etc.) are written to a **shared SQLite database**.

2. **Cyber step** — PLCs and SCADA read the latest sensor and actuator state from the database. They exchange data over the emulated network (subject to attacks and events). Each PLC and the SCADA apply their control logic (EPANET rules or your custom Python code) and write **actuator commands** (e.g. pump open/closed, valve open/closed) back to the database.

3. **Next hydraulic step** — The plant reads the actuator state from the database, applies it to the EPANET model, and runs the next hydraulic step. Then the cycle repeats.

So the **database** is the bridge: the hydraulic side writes “ground truth” sensor and actuator state; the cyber side reads that state (and what they see may be altered by attacks or network effects) and writes back the commands they decide. The plant always uses the **current** actuator state in the database to drive the next hydraulic step. That way, if an attack blocks or falsifies data, the PLCs or SCADA may issue wrong or stale commands, and you see the effect in the hydraulic results.

----------------------------------------
Why “who decides” matters
----------------------------------------

WaCSim supports three **control modes**:

- **PLC control** — Each PLC decides its own actuators using EPANET rules (or custom logic), using sensor data from the database and from other PLCs over the network. The SCADA only receives and records data; it does not send commands.

- **SCADA control** — All sensor data goes to the SCADA. The SCADA runs the control logic (rules or custom algorithms) and sends one command per actuator to the corresponding PLC. PLCs do not decide; they execute the SCADA’s command.

- **Hybrid control** — PLCs both talk to each other and to the SCADA. Each actuator PLC can receive a command from the SCADA *and* a local/peer-based decision. You can define how conflicts are resolved (e.g. PLC priority, SCADA priority, or a custom Conflict Resolution Algorithm).

The mode you choose changes where decisions are made and therefore how resilient the system is to attacks (e.g. DoS on one PLC vs on the SCADA link). The **Concepts → Control modes** section explains this in detail.

----------------------------------------
What you get at the end
----------------------------------------

After the run, WaCSim writes results under the **output path** (e.g. ``output/``) you set in the config:

- **CSV files** — ``ground_truth.csv`` (actual hydraulic state each step), ``scada_values.csv`` (what the SCADA received), and ``PLC1_values.csv`` … (what each PLC received). These let you compare “real” state vs what each control unit saw and how that affected behavior.

- **PCAP files** — Packet captures for the SCADA, each PLC, and each attacker. You can analyze them in Wireshark or in code to study traffic and attack signatures.

The **Concepts → Output files** section describes each file and how to use them together.

----------------------------------------
Where to go next
----------------------------------------

- **Input files** — What the main config, INP, PLC config, and optional attack/event/algorithm files do and where they live.
- **Control modes** — PLC vs SCADA vs Hybrid in depth.
- **Attacks** — Types of attacks and how to configure them.
- **Events** — Network delay and packet loss.
- **Custom algorithms** — Writing your own control or detection logic in Python.
- **Output files** — What each CSV and PCAP contains and how to use them.
- **Execution flow** — From ``wacsim config.yaml`` to the final output (conceptual).
