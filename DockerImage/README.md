# WaCSim Docker Containerization Manual

This directory contains the Docker configuration files needed to build and run the WaCSim cyber-physical co-simulation framework inside a container. Containerization resolves all platform dependency issues and isolates Mininet network emulation safely.

---

## Files in this Directory

- **`Dockerfile`**: Defines the step-by-step container environment. It builds on Ubuntu 22.04, installs network tools (`openvswitch-switch`, `iptables`, `tcpdump`, etc.), clones and installs the required network libraries (Mininet, MiniCPS, epynet, python-netfilterqueue), and installs WaCSim itself.
- **`entrypoint.sh`**: A helper script executed when the container starts. It boots the Open vSwitch daemon (`ovsdb-server` and `ovs-vswitchd`) which is required by Mininet for emulation before executing user commands.

---

## Prerequisites

- **Docker** must be installed on your host system:
  ```bash
  sudo apt-get update && sudo apt-get install -y docker.io
  ```

---

## 1. How to Build the Image

To build the WaCSim Docker image, run the following command **from the root of the WaCSim repository**:

```bash
docker build -t wacsim -f DockerImage/Dockerfile .
```

- `-t wacsim`: Tags the resulting image as `wacsim`.
- `-f DockerImage/Dockerfile`: Tells Docker to use the Dockerfile inside this subdirectory.
- `.`: The build context (root of the repository).

Building the image will take about 2–3 minutes as it downloads and compiles Mininet and virtual switches.

---

## 2. How to Run Simulations

### Critical Execution Requirement: `--privileged`
Because WaCSim and Mininet modify virtual network namespaces, interfaces, routing tables, and access kernel-level packet filters, **you must run the container with the `--privileged` flag**. 

### Command Template

To run a simulation and have access to the configuration files and outputs locally, run:

```bash
docker run --privileged -v $(pwd):/workspace -w /workspace -it wacsim wacsim <path_to_config.yaml>
```

### Explanation of flags:
- `--privileged`: Grants the container access to host networking and kernel functions (mandatory for Mininet).
- `-v $(pwd):/workspace`: Mounts your current directory on the host to `/workspace` inside the container. This ensures that any input files are read and output files (CSVs, PCAPs) are saved back to your host filesystem.
- `-w /workspace`: Sets the working directory inside the container to the mounted folder.
- `-it`: Runs the container interactively.
- `wacsim <config.yaml>`: Executes the WaCSim runner on your configuration file.

### Example Run (EdenTown Vanilla)

Run the Getting Started example from the repository root:

```bash
docker run --privileged -v $(pwd):/workspace -w /workspace -it wacsim wacsim examples/GettingStartedEdenTown/config.yaml
```

The output CSV files and network PCAP captures will appear in the `output/` directory in your local workspace.
