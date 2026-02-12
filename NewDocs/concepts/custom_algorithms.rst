.. B.6 Custom algorithms (decision makers)
.. WaCSim User Manual

========================================
Custom algorithms
========================================

Custom algorithms let you replace or extend the built-in control logic (EPANET rules from the INP file) with **your own Python code**. You can run custom decision logic on the **PLC** (per actuator), on the **SCADA** (per actuator), or in **hybrid** mode where the PLC can use both local rules and SCADA commands. This section is the main reference for how to configure and implement custom algorithms.

----------------------------------------
What custom algorithms are
----------------------------------------

- **Built-in behaviour:** By default, each actuator is controlled by **rules** defined in the EPANET INP file (e.g. “if tank T1 below 3 m then open pump P1”). Those rules are parsed and applied by the PLC or SCADA depending on the control mode.
- **Custom algorithm:** Instead of (or in addition to) that, you can assign a **decision maker** to an actuator. The decision maker can be:
  - **``rule``** — Use the INP rule (default).
  - **``scada``** — (Hybrid only.) Use the command sent by the SCADA.
  - **``open``** / **``closed``** — (Hybrid only.) Force that actuator to open or closed regardless of rules or SCADA.
  - **A path to a Python file** — Your script is loaded and its **``AlgoRun``** function is called each time that actuator’s decision is needed. The function receives current sensor/actuator data and returns what to do (e.g. ``'open'``, ``'closed'``, or a pump speed).

Custom algorithms run **inside** the PLC or SCADA process, once per simulation iteration, for each actuator that has a script path. They have access to the same data the built-in logic sees (local cache, remote/dependent sensor values, and in hybrid mode the SCADA cache and the control object). 

----------------------------------------
Where they run
----------------------------------------

- **PLC control (``plccontrol``):** Only **``decision_maker_per_plc``** is used. Each PLC loads its decision-maker config; for each actuator that has a script path, the PLC calls ``AlgoRun`` with the PLC’s cache and local sensor/actuator values. The SCADA does not run actuator decision logic.
- **SCADA control (``scadacontrol``):** Only **``decision_maker_per_scadacommand``** is used. The SCADA runs the control loop; for each actuator that has a script path, the SCADA calls ``AlgoRun`` with the current row of its cache (all tags from all PLCs for that iteration). The result is sent as the ScadaCommand for that actuator.
- **Hybrid control (``hybridcontrol``):** Both configs can be used. The **SCADA** uses ``decision_maker_per_scadacommand`` to decide what command to send per actuator (or ``rule`` to use INP-based logic). The **PLC** uses ``decision_maker_per_plc`` to decide, per actuator, whether to apply the local rule (``rule``), the SCADA command (``scada``), a fixed open/closed, or a custom script. In hybrid, the PLC’s ``AlgoRun`` (if used) receives the SCADA cache and the control object so it can implement conflict resolution or combined logic.

See :doc:`control_modes` for how data flows in each mode.

----------------------------------------
Config file structure
----------------------------------------

You reference decision-maker config from the **main config** with:

- **``decision_maker_per_plc: !include <file>.yaml``** — Per-PLC, per-actuator decision maker (used in PLC and hybrid modes).
- **``decision_maker_per_scadacommand: !include <file>.yaml``** — Per-actuator decision maker for the SCADA (used in SCADA and hybrid modes).

**decision_maker_per_plc** (YAML list, one entry per PLC):

.. code-block:: yaml

   decision_maker_per_plc: !include my_decision_plc.yaml

Content of ``my_decision_plc.yaml``:

.. code-block:: yaml

   - name: PLC1
     actuators:
       - name: P1
         decision_maker: rule
       - name: V4
         decision_maker: PLCAlgos/V4_Algo.py
         dependents: [T2, J4]
   - name: PLC2
     actuators:
       - name: P2
         decision_maker: Algos/P2_speed.py
         dependents: [T1, T2]

- **``name``** — PLC name (must match a PLC in ``plcs``).
- **``actuators``** — List of actuators belonging to that PLC. Each entry has:
  - **``name``** — Actuator name (e.g. ``P1``, ``V4``). Must match an actuator in the INP (or see “Actuators with no INP control” below).
  - **``decision_maker``** — ``rule``, or a **path to a Python file** (e.g. ``PLCAlgos/V4_Algo.py``). In **hybrid** mode only, you can also use ``scada``, ``open``, or ``closed``.
  - **``dependents``** (optional but recommended for custom scripts) — List of **sensor names** (e.g. ``[T1, J5]``) that the algorithm needs. WaCSim adds these to the PLC’s dependent-sensor list so their values are fetched and available in the cache. Required if the actuator has **no** control in the INP (synthetic control case).

**decision_maker_per_scadacommand** (YAML list, one entry per PLC whose actuators the SCADA controls):

.. code-block:: yaml

   decision_maker_per_scadacommand: !include my_decision_scada.yaml

Content of ``my_decision_scada.yaml``:

.. code-block:: yaml

   - name: PLC1
     actuators:
       - name: P1
         decision_maker: ScadaAlgos/Scada_P1_Algo.py
       - name: P2
         decision_maker: rule
       - name: V4
         decision_maker: ScadaAlgos/V4_Algo.py
         Hybrid_Values_To_Send: [T2, J4]
   - name: PLC2
     actuators:
       - name: P2
         decision_maker: rule

- **``name``** — PLC name.
- **``actuators``** — Each entry has **``name``**, **``decision_maker``** (``rule`` or path to Python), and optionally:
  - **``dependents``** — Sensor names the SCADA algorithm needs (if any).
  - **``Hybrid_Values_To_Send``** — (Hybrid mode only.) List of **sensor names** the SCADA should send to **this PLC** with an ``S`` suffix (e.g. ``T2`` → ``T2S``). The PLC’s cache is updated with these values so the PLC (or its custom algorithm) can use them. Use this when the PLC’s decision logic needs sensor values that are not on that PLC’s INP-dependent list.

**Path resolution:** All paths (script paths, ``dependents``, ``Hybrid_Values_To_Send``) are relative to the **directory of the main config file**. Place your script next to the config or in a subdirectory (e.g. ``PLCAlgos/P1_Algo.py``).

----------------------------------------
Dependents: why and how
----------------------------------------

- **PLC:** A PLC only receives sensor values for tags it “owns” (local sensors) and for **dependent sensors** (those listed in the INP ``[CONTROLS]`` dependant field or in the PLC’s ``dependent_sensors`` / ``dependant_sensors`` in the generated config). Your custom algorithm receives a **plc_cache** dict (remote/dependent tag → value) and a **plc_dict** (local sensor/actuator → value). If your script needs a sensor that is not already a dependent (e.g. a tank on another PLC), you **must** list it in **``dependents``** for that actuator. The parser then adds those names to the PLC’s dependent-sensor list so the values are fetched and present in the cache.
- **SCADA:** The SCADA already has all PLC sensor and actuator tags in its cache (one row per iteration). So for SCADA algorithms you typically do not need to add dependents unless you rely on some extra tags; the cache row passed to ``AlgoRun`` contains the usual SCADA view.

----------------------------------------
Actuators with no INP control (synthetic controls)
----------------------------------------

If an actuator has a **custom algorithm** (script path) but **no** control rule in the INP file, that actuator would otherwise never be in the control loop. WaCSim handles this by **synthetic controls**:

- When the config is parsed, the code looks at every actuator that has a custom decision maker (script path) and checks whether that actuator appears in any INP ``[CONTROLS]`` rule for its PLC.
- If it does **not**, a **synthetic TIME control** is added: one rule “at time 0 set this actuator to open”. That gets the actuator into the control loop. On every iteration, your **custom algorithm** runs and decides the actual state (open, closed, or pump speed); the synthetic rule only ensures the loop executes for that actuator.
- For this to work, you **must** provide **``dependents``** for that actuator so the PLC has the sensor data your script needs. The parser requires dependents when creating synthetic controls.

----------------------------------------
The ``AlgoRun`` interface
----------------------------------------

Your Python file **must** define a function named **``AlgoRun``**. It is called once per iteration for each actuator that uses that script. The **signature and return value** depend on where it runs.

----------------------------------------
PLC mode: ``AlgoRun(plc_cache, plc_dict)``
----------------------------------------

Used when the PLC runs your script (PLC control or hybrid with a script path for that actuator).

**Arguments:**

- **``plc_cache``** — A **dict** mapping tag identifiers (e.g. ``'T1'`` or ``('T1', 1)``) to **float** values. Contains the current values of **dependent/remote** sensors and any tags the PLC receives from other PLCs or the SCADA (e.g. ``T2S`` in hybrid). Updated each iteration before ``AlgoRun`` is called.
- **``plc_dict``** — A **dict** mapping tag identifiers to **float** values: the **local** sensor and actuator values for this PLC at the current iteration (same structure as ``get_system_state()``). Keys may be strings like ``'T1'`` or tuples like ``('T1', 1)`` depending on the runtime; support both if you want to be safe.

**Return:**

- **``'rule'``** — Apply the INP rule for this actuator (if any).
- **``'open'``** — Set actuator to open.
- **``'closed'``** — Set actuator to closed.
- **Numeric (float)** — For pumps: set speed in range **0.0–2.0** (e.g. 1.0 = normal, 0.0 = off).
- **Tuple ``(result, skip_flag)``** — Same as above for ``result``; if ``skip_flag`` is ``True``, no further controls for this actuator are applied this iteration (avoids duplicate application when multiple controls target the same actuator).

**Example (PLC, two arguments):**

.. code-block:: python

   def AlgoRun(plc_cache, plc_dict):
       # Get tank level; keys may be ('T1', 1) or 'T1'
       t1 = plc_dict.get(('T1', 1)) or plc_dict.get('T1')
       if t1 is None and plc_cache:
           t1 = plc_cache.get('T1') or plc_cache.get(('T1', 1))
       if t1 is None:
           return 'rule'
       if t1 < 3.0:
           return 'open'
       if t1 > 7.0:
           return 'closed'
       return 'rule'

----------------------------------------
Hybrid mode (PLC): ``AlgoRun(plc_cache, plc_dict, scada_cache, control)``
----------------------------------------

When the **PLC** runs your script in **hybrid** mode, two extra arguments are passed:

- **``scada_cache``** — A **dict** of SCADA-related tags for the current iteration, e.g. ``ScadaCommand_P1`` (the command the SCADA sent for actuator P1). Your algorithm can use this to implement conflict resolution (e.g. follow SCADA only if local sensor is bad).
- **``control``** — The **control object** for this actuator. It has at least **``control.actuator``** (the actuator name, e.g. ``'P1'``). You can use it to know which actuator you are deciding for.

Return values are the same as in PLC mode (``'rule'``, ``'open'``, ``'closed'``, numeric, or tuple with skip flag).

**Example (hybrid, four arguments):**

.. code-block:: python

   def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
       t1 = plc_dict.get(('T1', 1)) or plc_dict.get('T1')
       scada_cmd = scada_cache.get('ScadaCommand_' + control.actuator) if scada_cache else None
       if t1 is None:
           return 'scada' if scada_cmd is not None else 'rule'
       if t1 < 2.0:
           return 'open'
       if t1 > 8.0:
           return 'closed'
       return scada_cmd if scada_cmd is not None else 'rule'

----------------------------------------
SCADA mode: ``AlgoRun(cache_row)``
----------------------------------------

Used when the **SCADA** runs your script (SCADA or hybrid mode, with a script path in ``decision_maker_per_scadacommand``).

**Arguments:**

- **``cache_row``** — A **pandas Series** (one row of the SCADA cache for the current iteration). Index is tag names: all sensors and actuators from all PLCs (e.g. ``T1``, ``T2``, ``P1``, ``P2``), plus ``ScadaCommand_<actuator>`` if applicable. Use ``cache_row['T1']``, ``cache_row['P1']``, etc. to read current values.

**Return:**

- Same as PLC: ``'rule'`` (use INP-based SCADA decision), ``'open'``, ``'closed'``, numeric pump speed (0.0–2.0), or tuple ``(result, skip_flag)``.

**Example (SCADA, one argument):**

.. code-block:: python

   import pandas as pd

   def AlgoRun(cache_dict: pd.Series):
       t1 = cache_dict.get('T1', 0)
       if t1 < 3.0:
           return 'open'
       if t1 > 7.0:
           return 'closed'
       return 'rule'

----------------------------------------
Summary table
----------------------------------------

+------------------+------------------------------------------+------------------------------------------+
| Context          | Arguments                                | Return                                    |
+==================+==========================================+==========================================+
| PLC (PLC mode)   | ``plc_cache``, ``plc_dict``              | ``'rule'``, ``'open'``, ``'closed'``,    |
|                  |                                          | float 0.0–2.0, or ``(result, skip_flag)`` |
+------------------+------------------------------------------+------------------------------------------+
| PLC (hybrid)     | ``plc_cache``, ``plc_dict``,              | Same                                      |
|                  | ``scada_cache``, ``control``              |                                           |
+------------------+------------------------------------------+------------------------------------------+
| SCADA            | ``cache_row`` (pandas Series)             | Same                                      |
+------------------+------------------------------------------+------------------------------------------+

----------------------------------------
Hybrid_Values_To_Send (hybrid only)
----------------------------------------

In **hybrid** mode, the SCADA sends sensor values to PLCs for tags listed in **``Hybrid_Values_To_Send``** per actuator. Each value is written to the shared DB (and thus to the PLC’s view) with a tag name **suffix ``S``** (e.g. ``T2`` → ``T2S``). The PLC’s cache and its custom algorithm (if any) can then read ``T2S``, etc. Use this when the PLC’s logic or script needs a sensor that is not otherwise a dependent of that PLC.

----------------------------------------
Where configs live
----------------------------------------

- Create a YAML file (e.g. ``decision_plc.yaml`` or ``decision_scada.yaml``) in the **same directory** as your main config (or use paths relative to it).
- Use the list structure above: **``name``** (PLC name) and **``actuators``** with **``name``**, **``decision_maker``**, and optionally **``dependents``** and **``Hybrid_Values_To_Send``**.
- In the main config: ``decision_maker_per_plc: !include decision_plc.yaml`` and/or ``decision_maker_per_scadacommand: !include decision_scada.yaml``.
- Place your Python scripts in a subdirectory (e.g. ``PLCAlgos/``, ``ScadaAlgos/``) and reference them with paths relative to the main config directory (e.g. ``PLCAlgos/P1_Algo.py``).

Modules are **cached** per process: the first time an actuator uses a script, it is loaded; subsequent calls reuse the same module, so you can keep state in module-level variables if needed (e.g. for guard logic or filtering).

----------------------------------------
Recommendations
----------------------------------------

- **Prefer Python over INP rules for control.** Although you can still define controls in the INP file and override them per actuator with ``decision_maker`` (for backward compatibility), we **recommend** removing control rules from the INP ``[CONTROLS]`` section and implementing **all** logic in Python, including simple threshold rules. That way all behaviour lives in one place, is easier to version and test, and you can use synthetic controls (with **dependents**) for every actuator without mixing INP and YAML.

- **Use the ``dependents`` list** as in the examples. For each actuator that uses a custom script, list the sensor names your algorithm needs in **``dependents``**. This makes the data flow explicit, ensures the PLC (or SCADA) receives those values, and is **required** when the actuator has no INP control (synthetic control). Relying on INP-defined dependants only is possible but we recommend declaring dependents in the decision-maker config for clarity and consistency.
