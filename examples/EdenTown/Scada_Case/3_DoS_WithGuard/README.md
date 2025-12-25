# DoS Attack with Guard Algorithm - Scenario 3

## Overview

This scenario demonstrates a DoS (Denial of Service) attack on the water distribution 
network with a **guard algorithm** that mitigates the attack's impact.

## Attack Configuration

| Parameter | Value |
|-----------|-------|
| **Targets** | PLC2 (T1 sensor), PLC3 (T2 sensor) |
| **Duration** | Iterations 295-395 (100 iterations) |
| **Type** | `simple_dos` with `direction: source` |
| **Effect** | Blocks tank level readings from reaching SCADA |

## Guard Algorithm

### Purpose
When a DoS attack is detected (tank readings become stale), the guard algorithm 
takes over pump control using **historical median cycle times** to maintain 
reasonable tank levels without real-time sensor feedback.

### How It Works

1. **Normal Operation**: Algorithm reads T1 level and decides:
   - T1 < 6m → Turn pump ON
   - T1 > 7m → Turn pump OFF
   - Otherwise → Maintain current state

2. **DoS Detection**: When T1 readings stop changing (variance < 0.1 over 5 samples):
   - Calculate median ON/OFF durations from historical data
   - Continue pump cycling based on these medians
   - Track state in `GuardRoutineState.txt`

3. **Recovery**: When T1 readings start varying again:
   - Return to normal sensor-based control

### Algorithm Location
```
ScadaAlgos/
└── Scada_P1_Algo.py    # Guard algorithm for pump P1
```

## New Features Used (v0.5.1)

### Custom Algorithm Without INP Controls

This scenario uses the new v0.5.1 feature that allows custom algorithms 
**without requiring control rules in the INP file**.

**Before (old way):**
```
[CONTROLS]
LINK P1 OPEN IF NODE T1 BELOW 6      ; Required to "override"
LINK P1 CLOSED IF NODE T1 ABOVE 7    ; Required to "override"
```

**After (new way):**
```yaml
# EdenTown_decision_scada.yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: .../Scada_P1_Algo.py
      dependents: [T1]    # Specifies required sensors
```

WaCSim automatically creates a synthetic TIME control at iteration 0, 
ensuring the pump is in the control loop without needing INP rules.

### Benefits
- Cleaner INP files (no fake rules to override)
- Algorithm has full control from iteration 0
- No skip mechanism needed (single control per actuator)

## Files

| File | Description |
|------|-------------|
| `config.yaml` | Main configuration (500 iterations, scadacontrol mode) |
| `EdenTownScada.inp` | Network model (P2 has INP rules, P1 uses algorithm) |
| `EdenTownScada_plc.yaml` | PLC assignments |
| `EdenTown_decision_scada.yaml` | Decision maker configuration |
| `Plc3AndPlc2_Dos.yaml` | Attack definition |
| `ScadaAlgos/Scada_P1_Algo.py` | Guard algorithm |

## Running the Simulation

```bash
wacsim examples/EdenTown/Scada_Case/3_DoS_WithGuard/config.yaml
```

## Expected Results

| Phase | Iterations | P1 Behavior | T1 Level |
|-------|------------|-------------|----------|
| Normal | 0-294 | Sensor-based control | Oscillates 3-7m |
| Attack | 295-395 | Historical median cycling | Maintains ~3-7m range |
| Recovery | 396-500 | Returns to sensor-based | Stabilizes |

## Comparison with Scenario 2 (No Guard)

Without the guard algorithm, the pump maintains its last state throughout 
the attack, potentially causing:
- Tank overflow (if pump was ON)
- Tank empty (if pump was OFF)
- Service disruption

The guard algorithm prevents these issues by intelligently cycling the pump.

