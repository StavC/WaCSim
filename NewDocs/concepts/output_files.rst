.. B.7 Output files
.. WaCSim User Manual

========================================
Output files
========================================

After a run, WaCSim writes results under the path set by **``output_path``** in the main config (default: ``output``, relative to the config directory). This section describes the main files and how to use them together.

----------------------------------------
Where output goes
----------------------------------------

- **``output_path``** in the main config is the **directory** where CSVs and PCAPs are written. It is created if it does not exist.
- All paths in the config (INP, PLC YAML, attacks, etc.) are relative to the **config file** directory. The **output** directory is also resolved relative to the config file directory (e.g. ``output_path: output`` → ``<config_dir>/output/``).
- If you run from ``examples/GettingStartedEdenTown`` with ``output_path: output``, you get ``examples/GettingStartedEdenTown/output/``.

----------------------------------------
Main output files
----------------------------------------

**ground_truth.csv**
  Written by the **physical process** (hydraulic simulator). One row per iteration. Columns typically include iteration, timestamp, and the **true** state of all tanks, junctions, pumps, valves, and demands as seen by EPANET. This is the “real” system state before any cyber layer or attacks. Use it to compare what actually happened in the network with what the PLCs and SCADA saw or decided.

**scada_values.csv**
  Written by the **SCADA** process. One row per iteration. Contains iteration, timestamp, and the sensor/actuator values the SCADA **received** from the network (and, in SCADA/hybrid mode, the commands it sent). This is the SCADA’s view of the system. Compare with ``ground_truth.csv`` to see the effect of attacks or packet loss on the SCADA’s picture.

**<PLC_name>_values.csv** (e.g. ``PLC1_values.csv``, ``PLC4_values.csv``)
  Written by each **PLC** process. One row per iteration. Contains iteration, timestamp, and the tag values that PLC wrote to its local cache (sensors it owns, dependent sensors it received, and in SCADA/hybrid mode the ``ScadaCommand_*`` values). Use these to see what each PLC “thought” at each step and how that evolved under attacks or events.

**\*.pcap**
  Packet captures for each network interface (one per PLC, SCADA, router, attacker). For example: ``PLC1-eth0.pcap``, ``scada-eth0.pcap``, ``plc4Attac-eth0.pcap`` (attacker). Use Wireshark or ``tcpdump`` to inspect traffic (Ethernet/IP, CIP). Helpful to verify that attacks (e.g. DoS, MitM) actually occurred and how traffic was modified or dropped.

**water_loss.csv** / **demand_deficit.csv** (if produced)
  Written by the physical process when relevant metrics are computed (e.g. water loss, demand deficit). Content depends on the WaCSim version and options.

----------------------------------------
Configuration copy (optional)
----------------------------------------

WaCSim may write a **``configuration/``** subfolder under the output path with a copy of the intermediate config and related files used for that run. Useful for reproducibility and debugging.

----------------------------------------
Using the files together
----------------------------------------

- **Compare ground truth vs SCADA view:** Plot the same tag (e.g. tank level) from ``ground_truth.csv`` and ``scada_values.csv``. During an attack (e.g. DoS on a PLC), the SCADA may miss updates and show stale or missing values.
- **Compare PLC vs ground truth:** Plot a sensor from ``PLC2_values.csv`` and ``ground_truth.csv`` to see how that PLC’s view diverged when it was under attack or when links had loss/delay.
- **Inspect traffic:** Open the relevant ``*.pcap`` (e.g. attacker interface) to confirm packets were dropped or modified in the expected time window.
- **Reproducibility:** Re-run with the same config (and, if applicable, the same ``configuration/`` snapshot) to reproduce results.

See :doc:`execution_flow` for how these files are produced during a run.
