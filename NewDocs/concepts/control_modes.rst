.. B.3 Control modes (deep dive)
.. WaCSim User Manual

========================================
Control modes
========================================

The **control mode** (``mode`` in the main config) determines **who decides** the state of each actuator (pump or valve) and **how data flows** between PLCs and the SCADA. That in turn affects how resilient the system is to cyber-attacks and where you can plug in custom algorithms.

You set the mode in the main config YAML, e.g. ``mode: plccontrol``. Allowed values: ``plccontrol``, ``scadacontrol``, ``hybridcontrol``. **Default:** ``plccontrol``.

----------------------------------------
Why the mode matters
----------------------------------------

- In **PLC control**, each PLC decides its own actuators using sensor data it has (local + from other PLCs). The SCADA only receives and records data; it does not send commands. So if an attacker blocks or corrupts traffic to one PLC, that PLC’s decisions are affected (e.g. stale data), and the impact is local to what that PLC controls.

- In **SCADA control**, all sensor data goes to the SCADA. The SCADA runs the control logic and sends one command per actuator to the corresponding PLC. PLCs do not decide; they only execute the SCADA’s command. So simple Man-in-the-Middle attacks that only tamper with PLC-side traffic may be thwarted (the PLC still gets the SCADA command), but if the link to the SCADA is compromised or the SCADA’s view is wrong, all actuators can be affected.

- In **Hybrid control**, PLCs both talk to each other and to the SCADA. Each actuator PLC can receive a **local** decision (from EPANET rules or peer data) and a **SCADA** command. You define how conflicts are resolved (e.g. always follow PLC, always follow SCADA, or use a custom Conflict Resolution Algorithm in Python). This lets you study fallback, redundancy, and detection (e.g. compare SCADA view vs local view).

----------------------------------------
PLC control (``plccontrol``)
----------------------------------------

**Who decides:** Each PLC decides the state of its own actuators. The SCADA does **not** send actuator commands; it only receives and records data.

**Data flow:**

- Each PLC reads its **local sensors** (and any **dependent sensors** from the INP or config) from the shared database. Dependent sensor values are those that other PLCs “own”; WaCSim models PLC-to-PLC communication so that the PLC that needs a value (e.g. tank level) gets it from the PLC that has that sensor.
- PLCs **send** their sensor and actuator data to the SCADA over the network (so the SCADA can log ``scada_values.csv`` and monitor the system).
- PLCs **do not** receive commands from the SCADA for actuators. They apply the EPANET rules (from the INP ``[CONTROLS]``) or your **custom algorithms** (configured in ``decision_maker_per_plc``).

**When to use:**

- You want to study **decentralized** control: each PLC acts on local and peer data only.
- You are interested in **PLC-level attacks** (e.g. DoS or MiTM on one PLC) and their effect on that PLC’s decisions.
- You are running **custom algorithms only at the PLC** (no SCADA-side decision logic).

**Custom algorithms:** In this mode you can only attach custom decision logic at the PLC level (``decision_maker_per_plc``). The SCADA does not run control logic for actuators.

----------------------------------------
SCADA control (``scadacontrol``)
----------------------------------------

**Who decides:** The SCADA decides the state of every actuator. PLCs do not run control logic for actuators; they only execute the command the SCADA sends (open/closed or pump speed).

**Data flow:**

- Each PLC reads its local sensors from the database and **sends** all sensor (and actuator status) data **to the SCADA** over the network. PLCs **do not** exchange data with each other for the purpose of control; the SCADA is the only consumer of sensor data for decisions.
- The SCADA runs the control logic (EPANET rules or your **custom algorithms** in ``decision_maker_per_scadacommand``) and writes one command per actuator (e.g. ``ScadaCommand_P1``, ``ScadaCommand_V5``). Those commands are written to the shared database and sent to the PLCs.
- Each PLC reads the **SCADA command** for its actuators from the database and applies it (open/closed or speed). So the “decision” is entirely SCADA-side.

**When to use:**

- You want to study **centralized** control: one central unit sees all sensors and issues all commands.
- You are interested in **SCADA-level** algorithms (e.g. optimization, anomaly detection, or defense) or in attacks that target the SCADA link (e.g. replay, concealment).
- Simple MiTM attacks that only alter PLC–PLC or PLC-side traffic may not change behavior, because the actuator state is driven by the SCADA command.

**Custom algorithms:** In this mode you can only attach custom decision logic at the SCADA level (``decision_maker_per_scadacommand``). PLC-side ``decision_maker_per_plc`` is not used to decide actuator state; PLCs just execute the SCADA command.

----------------------------------------
Hybrid control (``hybridcontrol``)
----------------------------------------

**Who decides:** Both the PLC and the SCADA can produce a “decision” for an actuator. The **PLC is the final arbiter**: it receives (1) its own local/peer-based decision (from rules or a custom algorithm) and (2) the SCADA command (and optionally SCADA-sent sensor values). The PLC then applies one of three behaviors per actuator, depending on the **decision-maker** config for that actuator:

- **``rule``** — Use the local EPANET-rule result (PLC priority).
- **``scada``** — Use the SCADA command (SCADA priority).
- **Custom algorithm (path to .py)** — Run your Python code; it receives ``plc_cache``, ``LocalSensorsValues``, ``scada_cache``, and the control object, and returns the action (e.g. ``open``, ``closed``, or a pump speed). So you can implement your own **Conflict Resolution Algorithm (CRA)** (e.g. trust PLC if SCADA and PLC agree, else fallback; or detect inconsistency and switch to a safe state).

**Data flow:**

- PLCs send sensor and actuator data **to the SCADA** and **to other PLCs** (so dependent data is available for local rule evaluation and for custom PLC algorithms).
- The SCADA runs its control logic (rules or ``decision_maker_per_scadacommand``) and sends **commands** to each PLC (e.g. ``ScadaCommand_P1``). In addition, you can configure **``Hybrid_Values_To_Send``** in the SCADA decision-maker config: a list of sensor names (e.g. ``T1``, ``J1``) that the SCADA will send to the PLC with an **``S``** suffix (e.g. ``T1S``, ``J1S``). That way the PLC’s custom algorithm can compare “what the SCADA sees” (e.g. ``T1S``) with “what the PLC sees” (e.g. ``T1`` from peer or local) for anomaly or conflict detection.
- Each PLC, for each of its actuators, either applies ``rule``, applies the SCADA command, or runs a custom algorithm that can use both and return a single decision.

**When to use:**

- You want **redundancy** or **fallback**: e.g. normally follow SCADA, but if SCADA data is missing or inconsistent, follow local rule or a custom CRA.
- You are testing **Conflict Resolution Algorithms** or **attack detection** that compare SCADA view vs local/peer view (e.g. MiTM on one path).
- You need custom logic at **both** the SCADA and the PLC (e.g. SCADA sends setpoints or targets, PLC reconciles with local sensors).

**Custom algorithms:** You can use **both** ``decision_maker_per_plc`` and ``decision_maker_per_scadacommand``. The PLC’s algorithm receives ``scada_cache`` (including ``ScadaCommand_<actuator>`` and any ``<sensor>S`` values). See :doc:`custom_algorithms` and the ``Hybrid_Values_To_Send`` documentation for the exact interface.

----------------------------------------
Summary table
----------------------------------------

+------------------+----------------------+---------------------------+----------------------------------+----------------------------------------+
| Mode             | Who decides actuators| PLC–PLC data exchange     | SCADA role                       | Custom algorithms                     |
+==================+======================+===========================+==================================+========================================+
| ``plccontrol``   | PLC only             | Yes (for dependent data)  | Receive and record only          | PLC only (``decision_maker_per_plc``)  |
+------------------+----------------------+---------------------------+----------------------------------+----------------------------------------+
| ``scadacontrol`` | SCADA only           | No (for control)          | Decide and send commands         | SCADA only (``decision_maker_per_...  |
|                  |                      |                           |                                  | scadacommand``)                       |
+------------------+----------------------+---------------------------+----------------------------------+----------------------------------------+
| ``hybridcontrol``| PLC (final arbiter)  | Yes                       | Decide and send commands +       | Both PLC and SCADA; PLC can implement  |
|                  |                      |                           | optional ``Hybrid_Values_To_Send``| CRA using ``scada_cache``             |
+------------------+----------------------+---------------------------+----------------------------------+----------------------------------------+

----------------------------------------
Defaults when decision-maker is not set
----------------------------------------

If you do **not** configure ``decision_maker_per_plc`` or ``decision_maker_per_scadacommand``:

- **PLC control:** Every actuator uses **``rule``** (EPANET rules from the INP, using local and dependent sensor data).
- **SCADA control:** Every actuator follows the **SCADA command** (SCADA applies EPANET rules from the INP and sends the resulting command).
- **Hybrid control:** If you do not set a decision-maker for an actuator, the code treats it as **``rule``** (PLC applies local rule). To get SCADA priority or a custom CRA, you must configure the decision-maker for that actuator in ``decision_maker_per_plc`` (e.g. ``scada`` or path to a Python CRA).

See :doc:`custom_algorithms` for the full decision-maker options (``rule``, ``scada``, ``open``, ``closed``, or path to a script).
