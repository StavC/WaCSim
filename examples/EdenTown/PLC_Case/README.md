# NewPLC_Case - DoS Attack on PLC4

This directory contains two scenarios demonstrating a DoS attack on PLC4:

## Scenarios

### 1_INP_Controls
**Standard INP-based control rules (no custom algorithms)**

- Uses the `[CONTROLS]` section in the INP file for all actuator control
- No guard/defense mechanism against the attack
- Attack will disrupt normal operation

**Run command:**
```bash
wacsim examples/EdenTown/NewPLC_Case/1_INP_Controls/config.yaml
```

### 2_Custom_Algorithms  
**Custom algorithms with guard logic using the NEW interface**

- Uses the new WaCSim v0.5.1 feature: custom algorithms WITHOUT needing INP controls
- The `decision_plc.yaml` specifies algorithms with `dependents` field
- WaCSim automatically creates synthetic controls
- Includes guard logic to detect and respond to the attack

**Run command:**
```bash
wacsim examples/EdenTown/NewPLC_Case/2_Custom_Algorithms/config.yaml
```

## Attack Configuration

Both scenarios have the same attack:
- **Target:** PLC4 (controls pump P1)
- **Type:** Simple DoS (blocks incoming traffic)
- **Duration:** Iterations 145-245

## Network Topology

| PLC  | Sensors       | Actuators | Description |
|------|---------------|-----------|-------------|
| PLC1 | -             | P2        | Pump 2 control |
| PLC2 | T1, V5F, J5   | V5        | Valve 5 control (Tank 1) |
| PLC3 | T2, V4F, J4   | V4        | Valve 4 control (Tank 2) |
| PLC4 | J1, P1F, V1F  | P1        | Pump 1 control (attacked) |

## Custom Algorithm Logic

### P1_Algo.py (Pump Guard)
- Monitors P1 flow for sudden drops (attack indicator)
- When drop detected → closes pump P1
- Checks J1 pressure to know when to return to normal

### V4_Algo.py & V5_Algo.py (Valve Control)
- Monitor tank levels (T1, T2) and junction pressures (J4, J5)
- Use failsafe counter to prevent rapid valve cycling
- Open valve when tank full AND pump off

## Expected Results

- **Scenario 1 (INP Controls):** Attack disrupts normal operation
- **Scenario 2 (Custom Algorithms):** Guard detects attack and takes protective action

## Simulation Settings
- **Iterations:** 500
- **Mode:** plccontrol
- **Demand:** pdd (pressure-driven demand)

