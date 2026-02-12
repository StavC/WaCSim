.. Tutorial: Evolving GettingStartedEdenTown
.. WaCSim User Manual

========================================
Tutorial: Evolving GettingStartedEdenTown
========================================

This tutorial starts from the **GettingStartedEdenTown** example (vanilla PLC control, no attacks) and walks you through: **adding an attack**, **changing the control scheme** to see different behaviour, and **adding a simple custom algorithm**. You will run the same network under different configurations and compare results. Open questions at the end invite you to explore further.

**Prerequisites:** You have completed Part A (Quick Start) and run ``sudo wacsim config.yaml`` from ``examples/GettingStartedEdenTown`` at least once. You have read :doc:`../concepts/control_modes` and :doc:`../concepts/attacks` (at least in summary).

----------------------------------------
Step 1: Add an attack
----------------------------------------

We add a **Denial of Service (DoS)** attack on **PLC4** so that packets **to** PLC4 are dropped during part of the simulation. PLC4 controls pump P1; under DoS it may not receive sensor updates or may act on stale data.

**1.1** In the ``GettingStartedEdenTown`` folder you already have an example attack file: **``attacks_dos.yaml``**. Open it. It defines one network attack:

- **target:** PLC4  
- **type:** simple_dos  
- **direction:** destination (packets *to* PLC4 are dropped)  
- **trigger:** time, from iteration 30 to 70  

**1.2** In **``config.yaml``**, add the attacks include and (optionally) a distinct output folder so you can compare runs:

.. code-block:: yaml

   attacks: !include attacks_dos.yaml
   output_path: output_with_dos

**1.3** Run the simulation:

.. code-block:: bash

   cd examples/GettingStartedEdenTown
   sudo wacsim config.yaml

**1.4** Inspect the results in ``output_with_dos/``:

- **ground_truth.csv** — What actually happened in the network (tank levels, pump state).
- **scada_values.csv** — What the SCADA received (during the attack, PLC4’s data may be missing or stale).
- **PLC4_values.csv** — What PLC4 recorded (may freeze or diverge when it stops receiving updates).
- **\*.pcap** — Use Wireshark on the attacker or PLC4 interface to see that packets were dropped in the 30–70 window.

**Open questions to explore:**

- How do tank levels (e.g. in ``ground_truth.csv``) differ between the run *without* attacks (vanilla ``output/``) and this run? Does P1 stay on or off during the DoS?
- If you change **direction** to ``source``, so that packets *from* PLC4 are dropped instead, how does the SCADA’s view change? Who is affected more—the physical system or the operator’s picture?

----------------------------------------
Step 2: Change the control scheme
----------------------------------------

Now we keep the same attack file but **switch the control mode** so that the **SCADA** decides actuator commands instead of the PLCs. You will see that “who decides” changes how the system behaves under the same attack.

**2.1** In **``config.yaml``**, set:

.. code-block:: yaml

   mode: scadacontrol
   output_path: output_scada_under_dos

Leave ``attacks: !include attacks_dos.yaml`` in place.

**2.2** Run again:

.. code-block:: bash

   sudo wacsim config.yaml

**2.3** Compare with the previous run (PLC control under DoS):

- In **PLC control**, PLC4 could not receive updates from others or the SCADA during the attack, so it decided P1 on its own (possibly with stale data).
- In **SCADA control**, the SCADA decides P1 and sends a command to PLC4. If the attack drops packets *to* PLC4, PLC4 may not get the SCADA command and may keep the last state or default. How does **ground_truth.csv** (e.g. tank levels, P1 state) differ between ``output_with_dos`` (PLC) and ``output_scada_under_dos`` (SCADA)?

**Open questions to explore:**

- For this same DoS (destination), is the physical outcome “better” or “worse” under SCADA control than under PLC control? Why?
- Try **hybrid** mode: set ``mode: hybridcontrol``. You would need a ``decision_maker_per_scadacommand`` file to define who (PLC or SCADA) wins per actuator. How would you design a hybrid setup so that when PLC4 loses connectivity, the system degrades gracefully?

----------------------------------------
Step 3: Add a simple custom algorithm
----------------------------------------

We add a **custom decision maker** for pump **P1** (PLC4): a small Python script that replaces the INP rule with a simple threshold on junction **J1** pressure (pump on when pressure is low, off otherwise). This shows how to plug in your own logic even for a very simple rule.

**3.1** In the example folder you already have:

- **``decision_plc_tutorial.yaml``** — Assigns a custom script to P1 on PLC4 and declares **dependents: [J1]** so the algorithm gets J1.
- **``TutorialAlgos/simple_p1_guard.py``** — Defines **``AlgoRun(plc_cache, plc_dict)``** and returns ``'open'`` if J1 < 20, else ``'closed'`` (and ``'rule'`` if J1 is missing).

**3.2** In **``config.yaml``**, switch back to PLC control, remove the attack for a clean comparison, and add the decision maker:

.. code-block:: yaml

   mode: plccontrol
   output_path: output_custom_algo
   decision_maker_per_plc: !include decision_plc_tutorial.yaml
   # attacks: comment out or remove to run without attack

**3.3** Run:

.. code-block:: bash

   sudo wacsim config.yaml

**3.4** Check **output_custom_algo/PLC4_values.csv** and **ground_truth.csv**: P1 should now be driven by the Python logic (open when J1 < 20, closed otherwise) instead of the INP rule.

**Open questions to explore:**

- Change the threshold in ``simple_p1_guard.py`` (e.g. from 20 to 15 or 25). Re-run and compare tank levels and pump behaviour.
- Add the DoS attack again (``attacks: !include attacks_dos.yaml``) and run with the custom algorithm. Does PLC4 still have J1 in its cache during the attack? How does the combination of “custom logic” and “missing data” affect the outcome?
- Implement the same threshold logic for **SCADA** (create a small ``AlgoRun(cache_row)`` that reads ``cache_row['J1']`` and returns ``'open'`` or ``'closed'``). Use ``decision_maker_per_scadacommand`` and compare behaviour with the PLC-side custom algo.

----------------------------------------
Summary and next steps
----------------------------------------

- You added an attack (DoS on PLC4), changed the control mode (PLC vs SCADA), and ran a simple custom algorithm for P1.
- Use **output_path** to keep each run’s results separate and compare **ground_truth.csv**, **scada_values.csv**, and **PLC*_values.csv**.
- For more on attacks and options, see :doc:`../concepts/attacks`. For custom algorithms and the full ``AlgoRun`` interface, see :doc:`../concepts/custom_algorithms`. For running the paper scenarios (Ctown, EdenTown), see :doc:`paper_examples`.
