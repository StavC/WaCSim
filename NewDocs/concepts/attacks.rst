.. B.4 Attacks (deep dive)
.. WaCSim User Manual

========================================
Attacks
========================================

Attacks let you simulate malicious actors that disrupt or manipulate communication between PLCs and the SCADA. They are defined in a **separate YAML file** and referenced from the main config with ``attacks: !include <file>.yaml``. The included file can define **network attacks** (e.g. DoS, Man-in-the-Middle) and optionally **device attacks** (direct actuator override). This section is the main place for attack options and behaviour: how attacks fit in, common options, and each attack type.

----------------------------------------
How attacks fit in
----------------------------------------

- When you set ``attacks: !include my_attacks.yaml``, WaCSim loads that file. It must contain one or both of: **``network_attacks``** (list) and **``device_attacks``** (list).
- Each **network attack** runs as a separate process in the emulated network. It uses ARP poisoning (or similar) to sit between the target PLC and the rest of the network, then drops or modifies packets according to the attack type.
- **Device attacks** are attached to a specific PLC and actuator: when the trigger fires, the actuator is forced to a given state (e.g. open/closed or a pump speed) regardless of SCADA or PLC commands. They are useful for modeling direct device compromise.
- Every attack has a **trigger** that defines when it is active (e.g. between iterations 10 and 30, or when a sensor is below a threshold). When the trigger is not satisfied, the attack is inactive.

----------------------------------------
Config file structure
----------------------------------------

The included attack file has this shape:

.. code-block:: yaml

   network_attacks:
     - name: my_dos
       target: PLC2
       type: simple_dos
       direction: destination
       trigger:
         type: time
         start: 50
         end: 100
     - name: my_mitm
       target: PLC1
       type: mitm
       tags:
         - tag: T41
           value: 5.0
       trigger:
         type: time
         start: 20
         end: 80

   # Optional:
   device_attacks:
     - name: device_attack_1
       target: PLC3
       actuator: V4
       command: closed
       trigger:
         type: time
         start: 30
         end: 60

All paths inside the attack file (e.g. for concealment CSV) are relative to the **main config file** directory.

----------------------------------------
Common options (all attacks)
----------------------------------------

**name** (required)
  A unique label for the attack (used in logs and CSV output). No spaces or hyphens; use letters, numbers, underscores.

**trigger** (required)
  When the attack is active. Three forms:

  - **``time``** — Active from iteration ``start`` through iteration ``end`` (inclusive).

    .. code-block:: yaml

       trigger:
         type: time
         start: 10
         end: 30

  - **``below`` / ``above``** — Active when the given sensor is below (or above) a value. Can turn on and off multiple times as the sensor value crosses the threshold.

    .. code-block:: yaml

       trigger:
         type: below
         sensor: T41
         value: 4

  - **``between``** — Active when the sensor value is between ``lower_value`` and ``upper_value``.

    .. code-block:: yaml

       trigger:
         type: between
         sensor: T41
         lower_value: 2
         upper_value: 4

  The sensor name must match a tag that the target PLC (or the network) can provide.

----------------------------------------
Network attacks: target and type
----------------------------------------

**target** (required for network attacks)
  The **PLC name** (e.g. ``PLC1``, ``PLC4``) that this attack targets. For DoS and most MitM attacks, the attacker sits between that PLC and the rest of the network. Exact meaning can depend on **direction** (for DoS and naive MitM) and on the attack type (e.g. concealment targets the PLC that owns the modified tags).

**type** (required for network attacks)
  One of: ``simple_dos``, ``naive_mitm``, ``mitm``, ``server_mitm``, ``seq_mitm``, ``replay_mitm``, ``concealment_mitm``. See below for a short description and minimal example for each.

----------------------------------------
Denial of Service: ``simple_dos``
----------------------------------------

**What it does:** After ARP poisoning, the attacker intercepts packets and **does not forward** them. So either traffic **to** the target PLC or **from** the target PLC is dropped, depending on **direction**.

- **``direction: source``** (default) — Packets **from** the target PLC are dropped. Other PLCs and the SCADA do not receive that PLC’s sensor/actuator data. The target PLC can still receive traffic.
- **``direction: destination``** — Packets **to** the target PLC are dropped. The target PLC does not receive updates from other PLCs or from the SCADA; it may keep using stale values.

**Effect:** Victims see missing or frozen data; control decisions can be wrong (e.g. pump kept on because tank level was never updated). In PLC mode, a DoS on the PLC that provides a sensor can break the control loop that depends on that sensor.

**Minimal example:**

.. code-block:: yaml

   network_attacks:
     - name: plc4_dos
       target: PLC4
       type: simple_dos
       direction: destination
       trigger:
         type: time
         start: 100
         end: 200

----------------------------------------
Man-in-the-Middle (MitM) attacks
----------------------------------------

All MitM attacks first position the attacker between the target PLC and the network (e.g. via ARP poisoning). They then **intercept** and either **modify** or **replay** traffic.

----------------------------------------
Time-varying values: CSV path for value or offset
----------------------------------------

**Which attacks support it:** Only the **``mitm``** attack type supports using a **path to a CSV file** for ``value`` or ``offset``. The other MitM types use **numeric** value/offset only:

- **``mitm``** — CSV path supported for ``value`` and ``offset`` per tag (time-varying sequence).
- **``naive_mitm``**, **``server_mitm``**, **``concealment_mitm``**, **``seq_mitm``** — Only a single number for ``value`` or ``offset``; no CSV path.
- **``replay_mitm``** — Does not use ``value``/``offset`` (it replays captured traffic).

When using **``mitm``**, you can supply **time-varying** attack values by giving a path to a CSV instead of a single number:

- **``value``** — If you set ``value`` to a string that ends with ``.csv`` (e.g. ``attack_values_T41.csv``), the attacker loads one numeric value per row from that file. Each time it modifies a packet for that tag, it uses the **next** value in the list (and cycles back to the start when the list is exhausted). So you can define a sequence of overwrite values (e.g. ramping, step changes, or a recorded trajectory).
- **``offset``** — Similarly, ``offset`` can be a path to a CSV. Each row is one numeric offset; the attacker applies ``original_value + offset`` per packet, advancing through the file row by row (with wrap-around).

**CSV format:** One numeric value per row. The code reads the **first column** of each row; rows that look like a number (including floats) are used. No header is required (if the first row is numeric it will be used). Example:

.. code-block:: text

   5.0
   5.2
   5.5
   6.0
   4.0

**Path:** The path is relative to the working directory when the simulation runs (typically the directory of the main config file). Use a path relative to that (e.g. ``attack_data/T41_values.csv``) so the attack process can find the file.

**Why use it:** Fixed ``value`` or ``offset`` is enough for constant bias or step changes. A CSV path lets you simulate **progressive** or **scripted** deception (e.g. slowly drifting sensor readings, or replaying a precomputed attack profile) without writing a custom attacker script. For **periodic** or **formula-based** drift, ``seq_mitm`` with ``scaleParam`` and ``scaleTime`` is an alternative.

**Concealment (different CSV):** For ``concealment_mitm``, ``concealment_data`` can use ``type: path`` with a **different** CSV format: header row with column ``Iteration`` followed by one column per tag (e.g. ``T41``). Each row gives the simulation iteration and the concealment value(s) to send to the SCADA. That is separate from the value/offset CSV above (which only ``mitm`` supports). See the **concealment_mitm** subsection below for ``path``, ``payload_replay``, and ``network_replay``.

**Example (mitm with CSV value):**

.. code-block:: yaml

   - name: ramp_attack
     target: PLC1
     type: mitm
     tags:
       - tag: T41
         value: attack_data/T41_ramp.csv
       - tag: T42
         offset: offsets_T42.csv
     trigger:
       type: time
       start: 20
       end: 120

----------------------------------------
MitM attack types (summary)
----------------------------------------

**naive_mitm**
  Modifies **every** intercepted tag with a fixed **``value``** or **``offset``** (applied to all tags). No concealment; SCADA and other PLCs see the modified values. Optional **``direction``**: ``source`` (packets from target) or ``destination`` (packets to target).

  .. code-block:: yaml

     - name: naive_attack
       target: PLC1
       type: naive_mitm
       offset: 7.0
       trigger:
         type: time
         start: 50
         end: 150

**mitm**
  **Selective** tag modification. You list which tags to change under **``tags``**, each with ``value`` (overwrite) or ``offset`` (add to current value). For time-varying attacks, ``value`` or ``offset`` can be a **path to a CSV file** (see above). Only the listed tags are modified; the rest pass through.

  .. code-block:: yaml

     - name: selective_mitm
       target: PLC1
       type: mitm
       tags:
         - tag: T41
           value: 5.0
         - tag: T42
           offset: -2.0
       trigger:
         type: time
         start: 80
         end: 120

**server_mitm**
  Like ``mitm`` but only modifies packets **originating from** the target PLC (e.g. responses from that PLC). Uses **``tags``** with ``value`` or ``offset``; **numeric only** (no CSV path).

**seq_mitm** (sequential / scaled MitM)
  Same idea as ``mitm`` (selective tags with ``value`` or ``offset``), but the modification **changes over time**: every **``scaleTime``** iterations, **``scaleParam``** is added to the offset (or value). So the drift from the real value grows (or shrinks) over the attack window. Good for gradual deception. **Numeric** value/offset only (no CSV path).

  .. code-block:: yaml

     - name: drifting_mitm
       target: PLC1
       type: seq_mitm
       tags:
         - tag: T41
           offset: 0.5
           scaleParam: 0.1
           scaleTime: 5
       trigger:
         type: time
         start: 20
         end: 100

**replay_mitm**
  Does **not** modify payloads. The attacker **captures** packets from the target PLC (e.g. to the SCADA) over iterations **``capture_start``** to **``capture_end``**, then **replays** them starting at **``replay_start``**. So the SCADA (or other PLCs) see old traffic instead of live data.

  .. code-block:: yaml

     - name: replay_attack
       target: PLC2
       type: replay_mitm
       capture_start: 50
       capture_end: 100
       replay_start: 150
       trigger:
         type: time
         start: 50
         end: 200

**concealment_mitm**
  Modifies traffic as in ``mitm`` (via **``tags``**), but **hides** the attack from the SCADA using **``concealment_data``**: packets sent *to* the SCADA from the target PLC can be given different values. So the SCADA sees “normal” values while other PLCs (or the rest of the network) see the modified ones. Useful for stealthy deception. **Tags** and **concealment_value** use numeric ``value``/``offset`` only (no CSV path for value/offset). For time-varying concealment, use ``concealment_data`` ``type: path`` with the Iteration+tag CSV (see below).

  .. code-block:: yaml

     - name: concealed_mitm
       target: PLC2
       type: concealment_mitm
       tags:
         - tag: T41
           value: 2.0
       concealment_data:
         type: value
         concealment_value:
           - tag: T41
             value: 5.0
       trigger:
         type: time
         start: 100
         end: 180

  **Concealment_data types:**

  - **``type: value``** — Use ``concealment_value`` with a list of tag entries (each with ``tag`` and ``value`` or ``offset``). Numeric only (no CSV path for value/offset in concealment_mitm).
  - **``type: path``** — Use a single CSV file for all concealment values. The CSV has a header: ``Iteration`` plus one column per tag (e.g. ``T41``, ``T42``). Each row gives the iteration number and the value(s) to send to the SCADA for that iteration. Example: ``path: concealment_T41.csv`` with rows ``Iteration,T41`` and ``1,5``, ``7,6``, ``10,7``.
  - **``type: payload_replay``** — Capture tag values over a time window (``capture_start``, ``capture_end``), then replay those values starting at ``replay_start``. Only tag values are replayed, not full packets. The attack does not start until ``replay_start``, so the attacker remains concealed until then.
  - **``type: network_replay``** — Capture all packets over a window (``capture_start``, ``capture_end``) and replay them from ``replay_start`` (full-packet replay). As with ``payload_replay``, the attack does not begin until ``replay_start``, so the attacker remains concealed until then.

----------------------------------------
Device attacks
----------------------------------------

**What they do:** When the trigger is active, the specified **actuator** (pump or valve) is forced to a given **command**, regardless of what the PLC or SCADA decided. The attack is attached to the PLC that controls that actuator.

**Options:** ``target`` (PLC name), ``actuator`` (e.g. ``P1``, ``V5``), ``command``: ``open``, ``closed``, or a number (pump speed multiplier when using epynet). Same **trigger** as network attacks.

**Example:**

.. code-block:: yaml

   device_attacks:
     - name: force_valve_closed
       target: PLC3
       actuator: V4
       command: closed
       trigger:
         type: time
         start: 40
         end: 90

----------------------------------------
Where attack configs live
----------------------------------------

- Create a YAML file (e.g. ``my_attacks.yaml``) in the **same directory** as your main config (or in a subdirectory; paths inside the file are relative to the main config directory).
- Put **``network_attacks``** and/or **``device_attacks``** at the top level.
- In the main config: ``attacks: !include my_attacks.yaml``.
- You can have multiple attacks in one file (multiple list entries). Each network attack runs as its own process; each device attack is applied by the corresponding PLC when its trigger fires.
