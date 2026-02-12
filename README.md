# WaCSim — Water and Cyber Simulation

**WaCSim** is an open-source **cyber–physical digital twin** for water distribution systems. It simulates both the **hydraulic behaviour** of the network (tanks, pumps, valves, demands) and the **cyber layer** (PLCs, SCADA, network traffic, attacks and events) in a single, synchronized environment. That lets you study how control decisions, communication failures, and cyber-attacks affect the water system—and how the system responds.

WaCSim builds on [DHALSIM](https://github.com/Critical-Infrastructure-Systems-Lab/DHALSIM) and combines [EPANET](https://www.epa.gov/water-research/epanet) (via [WNTR](https://github.com/USEPA/WNTR) or [epynet](https://github.com/Vitens/epynet)) for hydraulics with [Mininet](https://github.com/mininet/mininet) and [MiniCPS](https://github.com/scy-phy/minicps) for the industrial control network.

---

## Features

- **Flexible control modes** — PLC control (decentralized), SCADA control (centralized), or hybrid (both, with configurable conflict resolution).
- **Custom algorithms** — Replace or extend INP rules with your own Python code per actuator (PLC or SCADA). Use synthetic controls so actuators need no INP rules.
- **Realistic attacks** — Denial of service (DoS), Man-in-the-Middle (MitM) variants (naive, selective, concealment, replay, sequential), and device attacks. Time- or sensor-triggered; optional CSV-driven time-varying values for MitM.
- **Network events** — Simulate delay and packet loss on links (triggered by time or sensor conditions) without running attack processes.
- **Configurable topology** — Simple (flat) or complex (per-PLC subnets) network layout; assign sensors, actuators, and dependent sensors per PLC.
- **Rich output** — Ground truth, SCADA view, per-PLC caches, and PCAPs for traffic analysis.

---

## Quick start

**Requirements:** Linux (or a Linux VM), `sudo`, Python 3. See [Installation](doc/installation.rst) for detailed setup (including VM).

1. **Clone and install**

   ```bash
   git clone <repository-url>
   cd WaCSim
   ./install.sh
   ```
   Replace `<repository-url>` with the actual clone URL.

2. **Run your first simulation**

   From the repo root:

   ```bash
   cd examples/GettingStartedEdenTown
   sudo wacsim config.yaml
   ```

   This runs the EdenTown network in **PLC control** mode for 100 iterations—no attacks, no custom algorithms. Output is written to `output/` in that folder (`ground_truth.csv`, `scada_values.csv`, `PLC*_values.csv`, and `*.pcap`).

   You can also pass an absolute or relative path to the config, e.g.  
   `sudo wacsim /path/to/WaCSim/examples/GettingStartedEdenTown/config.yaml`.

---

## Documentation

- **User manual (recommended)** — The [**NewDocs**](NewDocs/) folder contains the structured manual:
  - **Part A** — Quick Start (install, first run).
  - **Part B** — Concepts (control modes, attacks, events, custom algorithms, output files, execution flow).
  - **Part C** — Tutorials (evolving GettingStartedEdenTown, running the paper examples).

  Content is in reStructuredText (`.rst`); build with Sphinx from `doc/` if you include NewDocs in your toctree, or read the `.rst` files directly.

- **Legacy/reference docs** (in `doc/`) — [Getting started](doc/getting_started.rst), [Installation](doc/installation.rst), [Experiment config](doc/experiment_config_docs.rst), [Attack config](doc/attack_config_docs.rst), [Event config](doc/event_config_docs.rst), [Custom algorithms](doc/CustomAlgorithm.rst).

---

## Examples

| Example | Description |
|--------|-------------|
| [**GettingStartedEdenTown**](examples/GettingStartedEdenTown/) | Minimal vanilla run (PLC control, no attacks). Includes optional `attacks_dos.yaml` and a simple custom algorithm for the tutorials. |
| [**PaperExamples**](examples/PaperExamples/) | Configurations from the WaCSim paper: **Ctown** (hybrid + sequential MitM), **EdenTown PLC_Case** (DoS with/without custom guards), **EdenTown Scada_Case** (DoS with/without SCADA guard), **PumpSpeed** (variable pump speed via custom algorithms). Each scenario is self-contained; run from inside the scenario folder with `sudo wacsim config.yaml`. See [NewDocs/tutorials/paper_examples.rst](NewDocs/tutorials/paper_examples.rst). |
| **Other topologies** | `examples/` also includes Anytown, Ctown, EdenTown variants, ky3/ky14/ky15, Minitown, Wadi—each with configs and INP/PLC YAMLs. |

---

## License


