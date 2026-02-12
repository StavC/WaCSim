# Getting Started with WaCSim — EdenTown (vanilla PLC)

This folder contains a **minimal, vanilla** WaCSim example so you can run your first simulation without attacks or custom algorithms.

## What this example is

- **Network:** EdenTown — 2 reservoirs (R1, R2), 2 tanks (T1, T2), 2 pumps (P1, P2), 3 valves (V1, V4, V5), junctions J1–J5.
- **Control mode:** **PLC control** (`plccontrol`). PLCs exchange sensor data and apply the control rules defined in the INP file. SCADA only monitors (no commands).
- **No attacks, no events, no custom algorithms.** All pump/valve logic comes from the EPANET `[CONTROLS]` section in `EdenTown.inp`.

## How to run

From the **WaCSim repository root**:

```bash
cd examples/GettingStartedEdenTown
sudo wacsim config.yaml
```

Or from anywhere (use an absolute or relative path to the config):

```bash
sudo wacsim /path/to/WaCSim-master/examples/GettingStartedEdenTown/config.yaml
```

## What you get

- **Output folder:** `output/` (in this directory).
- **Files:** `ground_truth.csv`, `scada_values.csv`, `PLC1_values.csv` … `PLC4_values.csv`, and `*.pcap` network captures.

## Files in this folder

| File | Purpose |
|------|--------|
| `config.yaml` | Main WaCSim config (INP, PLCs, mode, iterations, demand). |
| `EdenTown_plc.yaml` | PLC definitions: which PLC has which sensors and actuators. |
| `EdenTown.inp` | EPANET network and control rules (tank levels → pumps/valves). |
| `demands_EdenTown.csv` | Demand pattern multipliers for the run. |

## Next steps

- Add a DoS attack: see the main manual (Tutorials) or copy an `attacks: !include ...` from `examples/EdenTown/PLC_Case/` and remove the attack file contents / use an empty list.
- Switch to SCADA or Hybrid mode: set `mode: scadacontrol` or `mode: hybridcontrol` in `config.yaml` (and add decision-maker configs if needed).
- Add custom algorithms: see **Concepts → Custom algorithms** and **Tutorials** in the user manual.
