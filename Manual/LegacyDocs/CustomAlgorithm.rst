Custom Algorithm Configuration
==============================

WaCSim allows per-actuator customization of control behavior through Python-based algorithms. These custom decision makers can override built-in control rules or SCADA commands. They are configured in YAML files and executed dynamically at runtime.

Overview
--------

Each actuator in the simulation can have one of the following control modes:

- `rule`: Use standard rule-based logic (e.g., Above/Below control).
- `scada`: Follow SCADA-issued command.
- `open` / `closed`: Force actuator state.
- `<path to .py>`: Execute a user-defined Python algorithm.

Custom algorithms can be used in **all simulation modes**:

- `plccontrol`: PLCs can run custom logic.
- `scadacontrol`: SCADA can run custom logic.
- `hybridcontrol`: SCADA and PLC can both run their own custom logic.

YAML Configuration
------------------

The following fields are used in the main config YAML:

.. code-block:: yaml

   decision_maker_per_plc: !include path/to/plc_decision.yaml
   decision_maker_per_scadacommand: !include path/to/scada_decision.yaml

Each file contains a list of devices with per-actuator configuration:

.. code-block:: yaml

   - name: PLC1
     actuators:
       - name: P1
         decision_maker: rule
       - name: P2
         decision_maker: scada
       - name: P3
         decision_maker: closed
       - name: P4
         decision_maker: custom_algos/my_algo.py

Accepted `decision_maker` values:

- `rule`: Use local rule-based logic (PLC or SCADA depending on context)
- `scada`: Use SCADA-issued command
- `open` / `closed`: Apply a fixed state
- `<file.py>`: Path to a Python script implementing a custom decision algorithm


Custom Algorithms Without INP File Controls (New Feature)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Important:** Previously, custom algorithms required a corresponding control rule in the INP file's ``[CONTROLS]`` section. **Now you can use custom algorithms without needing to define INP controls**.

When you specify a custom algorithm (a Python file path) as the ``decision_maker``, WaCSim will automatically:

1. Create a synthetic control for that actuator (so it gets evaluated every iteration)
2. Register any dependent sensors you specify
3. Execute your custom algorithm at each simulation step

**Configuration with Dependent Sensors (OPTIONAL):**

Specify the sensors your custom algorithm needs using the ``dependents`` field as a list:

.. code-block:: yaml

   - name: PLC1
     actuators:
       - name: P1
         decision_maker: custom_algos/tank_controller.py
         dependents: [T101]  # List of sensors the algorithm reads

**Multiple Dependent Sensors:**

You can specify multiple sensors that your algorithm needs:

.. code-block:: yaml

   - name: PLC2
     actuators:
       - name: P2
         decision_maker: custom_algos/multi_sensor_control.py
         dependents: [T101, T102, T103]  # Multiple sensors

**No Dependent Sensors:**

If your algorithm doesn't need sensors (e.g., time-based logic), omit the field or use empty list:

.. code-block:: yaml

   - name: PLC3
     actuators:
       - name: P3
         decision_maker: custom_algos/time_based_control.py
         # No dependents field needed, or use: dependents: []

This ensures:

- All sensors in the ``dependents`` list are properly registered (if provided)
- Sensor values are available in the algorithm's input dictionaries
- ONE synthetic TIME control is created at time 0 to get the actuator into the control loop
- The custom algorithm executes at every iteration and decides the actuator output

**Backward Compatibility:**

The original approach (defining controls in the INP file and using custom algorithms to override them) is still fully supported. If your INP file already has controls for an actuator, those controls will be used, and specifying a ``dependent`` in the YAML is optional.


Implementing Custom Algorithms
------------------------------

To implement a custom decision maker, researchers must create a Python script that defines a function named ``AlgoRun``. This function will be dynamically imported and executed during the simulation for each actuator assigned to the script.

Depending on whether the logic runs on the PLC or SCADA side, the function receives different arguments and is expected to return a specific set of values.
PLC-Side Custom Algorithm
^^^^^^^^^^^^^^^^^^^^^^^^^

In ``plccontrol`` and ``hybridcontrol``, the decision logic runs inside the PLC. Researchers must define the following function in their custom Python script:

.. code-block:: python

   def AlgoRun(plc_cache, plc_dict, scada_cache):
       return

**Arguments:**

- ``plc_cache``: A dictionary containing all current tag values for this PLC that were received from other PLCs over the network.
- ``plc_dict``: A dictionary of the PLC’s local tag values.
  - Includes all local sensors, dependent sensors, and actuator states.
- ``scada_cache`` (In Hybrid Mode): A dictionary of values sent from SCADA to the PLC.
  - Includes commands like ``ScadaCommand_<actuator>`` and, sensor mirror tags like ``<sensor>S``.

**Return Values:**

- ``"rule"``: Apply local PLC rule-based logic (e.g., Above/Below/Time control).
- ``"scada"``: Apply the SCADA-issued command for this actuator.
- ``"open"`` or ``"closed"``: Force the actuator to the specified state.
- Tuple: ``(result, skip)`` — optional return form where:
  - ``result`` is any of the above values.
  - ``skip`` is a boolean. If ``True``, this actuator will be **skipped** for the remainder of the control loop.

**Why use `skip`?**

In EPANET-style rule definitions, actuator behavior is often split across two separate control conditions — for example:

- Open if a sensor is **above** some threshold.
- Close if it is **below** another threshold.

A custom algorithm might choose to handle **both** conditions inside a single call to ``AlgoRun``. In such cases, there is no need to re-evaluate the actuator again later in the loop (e.g., due to another rule referencing the same actuator). Setting ``skip=True`` ensures the actuator is not processed twice, improving efficiency and avoiding redundant or conflicting behavior.



SCADA-Side Custom Algorithm
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In `scadacontrol` and `hybridcontrol`, SCADA determines the actuator command. for example:

.. code-block:: python

   def AlgoRun(cache_dict):
       if cache_dict["T42"] > 4.0:
           return "closed"
       return "open"

**Arguments:**
- ``cache_dict``: A dictionary containing all current tag values SCADA has received from all PLCs.

**Return Values:**

- ``"rule"``: Apply local PLC rule-based logic (e.g., Above/Below/Time control).
- ``"scada"``: Apply the SCADA-issued command for this actuator.
- ``"open"`` or ``"closed"``: Force the actuator to the specified state.
- Tuple: ``(result, skip)`` — optional return form where:
  - ``result`` is any of the above values.
  - ``skip`` is a boolean. If ``True``, this actuator will be **skipped** for the remainder of the control loop.

Default Behavior for Unspecified Actuators
------------------------------------------

If a decision maker is not provided for an actuator:

- In ``plccontrol`` and ``hybridcontrol``: the default is ``rule`` (local control logic).
- In ``scadacontrol``: the default is ``scada`` (follow SCADA command).

Execution Logic Summary
-----------------------

+-------------------+--------------------+---------------------------------------------+
| Mode              | Who makes decision | Custom Algorithms Allowed At                |
+===================+====================+=============================================+
| `plccontrol`      | PLC only           | Yes — via `decision_maker_per_plc`          |
+-------------------+--------------------+---------------------------------------------+
| `scadacontrol`    | SCADA only         | Yes — via `decision_maker_per_scadacommand` |
+-------------------+--------------------+---------------------------------------------+
| `hybridcontrol`   | Both               | Yes — at both PLC and SCADA                 |
+-------------------+--------------------+---------------------------------------------+


Advanced Notes
--------------

- Algorithms are dynamically loaded with `importlib.util`.
- Return values are logged and applied immediately to simulation state.
- All tag values and decisions are recorded in SCADA/PLC CSV logs.
- In ``hybridcontrol``, SCADA sends sensor values (with ``S`` suffix) to PLCs to enable hybrid-aware logic.

Real-Time Data Access
---------------------

Custom algorithms in WaCSim are executed at every simulation iteration and receive **live simulation data** through the input dictionaries described above:

- ``plc_dict``: Contains the real-time local state of the PLC, including all connected sensor readings.

- ``plc_cache``: Contains sensor or actuator values that the PLC has received from other PLCs across the network during the current iteration. This enables coordination or logic that depends on distributed information.

- ``scada_cache`` *(PLC-side only in ``hybridcontrol``)*: Contains the most recent commands and mirrored sensor values from SCADA. This gives the PLC visibility into what SCADA is trying to enforce or monitor.

- ``cache_dict`` *(SCADA-side)*: Represents the full set of sensor and actuator values that SCADA has received from all PLCs. It includes everything SCADA currently knows about the system state and is updated in real time.

Because ``AlgoRun`` is just a regular Python function, **researchers are free to integrate any additional logic or external tools** into their algorithms. For example, a custom script can:

- Write values to an external file or database.
- Load and evaluate machine learning models to make decisions.
- Track historical trends across iterations using global variables or files.
- Open and parse `.pcap` network traffic files being written by the simulator.
- Apply statistical or control-theoretic logic using any Python package (e.g., `numpy`, `scikit-learn`, `pandas`, etc.).

This design enables **highly expressive control strategies**, ideal for experimenting with:
- Intrusion detection systems,
- Anomaly detection,
- Data-driven control policies,
- or coordinated multi-agent logic across PLCs.

There are no constraints on which packages can be used, as long as the logic complies with standard Python and returns one of the supported control values.

