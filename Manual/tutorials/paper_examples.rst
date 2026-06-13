.. Tutorial: Running the paper examples
.. WaCSim User Manual

========================================
Tutorial: Running the paper examples
========================================

The **PaperExamples** folder contains the configurations used in the WaCSim paper. Each scenario is **self-contained**: a subfolder holds its own ``config.yaml``, INP file, PLC/attack/decision-maker files, and (after a run) an output directory. You run WaCSim from **inside** that scenario folder so that relative paths in the config resolve correctly.

**Prerequisites:** WaCSim is installed (Part A). You need ``sudo`` (required for Mininet). All commands below assume you are in the **repository root** for the ``cd`` paths.

----------------------------------------
Overview
----------------------------------------

- **``examples/PaperExamples/Ctown/``** — Ctown network (``ctown_map.inp``), **hybrid** control, sequential MitM attack. One top-level config: ``ctown_config.yaml``. Run from **Ctown/**.

- **``examples/PaperExamples/EdenTown/``** — EdenTown scenarios in three groups:

  - **PLC_Case/** — PLC control, DoS on PLC4. Two scenarios:
    - **1_INP_Controls** — INP rules only, no custom algorithms.
    - **2_Custom_Algorithms** — Custom algorithms (guards) on P1, V4, V5; synthetic controls.
  - **Scada_Case/** — SCADA control, EdenTownScada network. Three scenarios:
    - **1_NoAttack** — No attack; baseline.
    - **2_DoS_NoGuard** — DoS on PLC2 and PLC3; no guard.
    - **3_DoS_WithGuard** — Same DoS; SCADA runs a guard algorithm for P1.
  - **PumpSpeed_CustomAlgo_Example/** — Variable pump speed (0.0–2.0) via custom algorithms; no attacks. Run from this folder.

----------------------------------------
Ctown
----------------------------------------

**Directory:** ``examples/PaperExamples/Ctown/``

**Config:** ``ctown_config.yaml`` — ``ctown_map.inp``, ``ctown_plcs.yaml``, ``ctown_decision_plc.yaml``, ``ctown_Seqmitm.yaml``. Mode: **hybrid**. Output: **CtownTestingTwoAttacks**.

**Run:**

.. code-block:: bash

   cd examples/PaperExamples/Ctown
   sudo wacsim ctown_config.yaml

**Output:** ``CtownTestingTwoAttacks/`` (ground_truth.csv, scada_values.csv, PLC1–PLC9 values, PCAPs). Uses **complex** topology and **sequential MitM**; run time is longer than EdenTown.

----------------------------------------
EdenTown PLC_Case (DoS on PLC4)
----------------------------------------

Two scenarios share the same attack (DoS on PLC4, iterations 145–245) but differ in control: INP rules only vs custom algorithms with guards.

**1_INP_Controls — INP rules only**

.. code-block:: bash

   cd examples/PaperExamples/EdenTown/PLC_Case/1_INP_Controls
   sudo wacsim config.yaml

**Output:** ``output/``. No guard; attack disrupts normal operation.

**2_Custom_Algorithms — Custom algorithms (guards)**

.. code-block:: bash

   cd examples/PaperExamples/EdenTown/PLC_Case/2_Custom_Algorithms
   sudo wacsim config.yaml

**Output:** ``output/``. Guard logic on P1, V4, V5; synthetic controls (no INP rules needed for those actuators). Compare with 1_INP_Controls to see the effect of the guards.

----------------------------------------
EdenTown Scada_Case
----------------------------------------

Three scenarios: no attack, DoS without guard, DoS with guard. Each scenario is in its own subfolder with its own ``config.yaml`` and files.

**1_NoAttack — Baseline (no attack)**

.. code-block:: bash

   cd examples/PaperExamples/EdenTown/Scada_Case/1_NoAttack
   sudo wacsim config.yaml

**Output:** ``output/``.

**2_DoS_NoGuard — DoS on PLC2 and PLC3, no guard**

.. code-block:: bash

   cd examples/PaperExamples/EdenTown/Scada_Case/2_DoS_NoGuard
   sudo wacsim config.yaml

**Output:** ``outputNew2/``. Attack blocks tank readings (T1, T2) from reaching SCADA; pump P1 keeps last state.

**3_DoS_WithGuard — Same DoS, SCADA guard algorithm for P1**

.. code-block:: bash

   cd examples/PaperExamples/EdenTown/Scada_Case/3_DoS_WithGuard
   sudo wacsim config.yaml

**Output:** ``outputNew3/``. Guard detects stale T1 and switches to median-based cycling. For a clean run, clear guard state first:

.. code-block:: bash

   rm -f ScadaAlgos/ScadaData/*
   sudo wacsim config.yaml

Compare ``outputNew3/`` with ``outputNew2/`` (no guard) to see how the guard mitigates the DoS impact.

----------------------------------------
EdenTown PumpSpeed_CustomAlgo_Example
----------------------------------------

Variable pump speed (0.0–2.0) via custom algorithms; no INP controls for P1/P2; no attacks.

**Directory:** ``examples/PaperExamples/EdenTown/PumpSpeed_CustomAlgo_Example/``

**Config:** ``EdenTown_PumpSpeed_config.yaml``. Demand patterns path is ``../PLC_Case/demands_EdenTown.csv``. In the current layout that path does not exist (demands live under ``PLC_Case/1_INP_Controls`` or ``2_Custom_Algorithms``). If the run fails on demand_patterns, set ``demand_patterns`` in the config to a valid path, e.g. ``../PLC_Case/2_Custom_Algorithms/demands_EdenTown.csv``, or copy a demands CSV into this folder and reference it.

**Run:**

.. code-block:: bash

   cd examples/PaperExamples/EdenTown/PumpSpeed_CustomAlgo_Example
   sudo wacsim EdenTown_PumpSpeed_config.yaml

**Output:** ``PumpSpeed_Demo_Output/``.

----------------------------------------
Summary table
----------------------------------------

+------------------+---------------------------------------------------+------------------------------------------+------------------+
| Example          | Directory (from repo root)                        | Command                                   | Output           |
+==================+===================================================+==========================================+==================+
| Ctown            | ``PaperExamples/Ctown``                          | ``sudo wacsim ctown_config.yaml``         | CtownTestingTwoAttacks |
+------------------+---------------------------------------------------+------------------------------------------+------------------+
| EdenTown PLC     | ``PaperExamples/EdenTown/PLC_Case/1_INP_Controls``   | ``sudo wacsim config.yaml``          | output           |
| (INP only)       |                                                   |                                          |                  |
+------------------+---------------------------------------------------+------------------------------------------+------------------+
| EdenTown PLC     | ``PaperExamples/EdenTown/PLC_Case/2_Custom_Algorithms`` | ``sudo wacsim config.yaml``        | output           |
| (custom algos)   |                                                   |                                          |                  |
+------------------+---------------------------------------------------+------------------------------------------+------------------+
| EdenTown SCADA   | ``PaperExamples/EdenTown/Scada_Case/1_NoAttack``  | ``sudo wacsim config.yaml``               | output           |
| (no attack)      |                                                   |                                          |                  |
+------------------+---------------------------------------------------+------------------------------------------+------------------+
| EdenTown SCADA   | ``PaperExamples/EdenTown/Scada_Case/2_DoS_NoGuard`` | ``sudo wacsim config.yaml``            | outputNew2       |
| (DoS, no guard)  |                                                   |                                          |                  |
+------------------+---------------------------------------------------+------------------------------------------+------------------+
| EdenTown SCADA   | ``PaperExamples/EdenTown/Scada_Case/3_DoS_WithGuard`` | ``sudo wacsim config.yaml``           | outputNew3       |
| (DoS + guard)    |                                                   |                                          |                  |
+------------------+---------------------------------------------------+------------------------------------------+------------------+
| EdenTown         | ``PaperExamples/EdenTown/PumpSpeed_CustomAlgo_Example`` | ``sudo wacsim EdenTown_PumpSpeed_config.yaml`` | PumpSpeed_Demo_Output |
| PumpSpeed        |                                                   |                                          |                  |
+------------------+---------------------------------------------------+------------------------------------------+------------------+

----------------------------------------
Notes
----------------------------------------

- **Always run from the scenario directory** (the folder that contains the ``config.yaml`` you pass to ``wacsim``). All paths in the config (INP, plcs, attacks, demand_patterns, etc.) are relative to that directory.
- **Pre-run output:** Some scenario folders already contain ``output/`` or ``outputNew*/`` from previous runs. Re-running overwrites those unless you change ``output_path`` in the config.
- **Log level:** Many configs use ``log_level: debug``. Use ``info`` in the config for quieter runs.
- **Guard state (3_DoS_WithGuard):** Clearing ``ScadaAlgos/ScadaData/*`` before a run gives a clean guard state; see the scenario’s README.
