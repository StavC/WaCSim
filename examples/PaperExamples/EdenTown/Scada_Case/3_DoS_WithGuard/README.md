# DoS Attack with Guard Algorithm - Scenario 3

## Overview

This scenario demonstrates a DoS (Denial of Service) attack on the water distribution 
network with a **guard algorithm** that mitigates the attack's impact.

## Attack Configuration

| Parameter | Value |
|-----------|-------|
| **Targets** | PLC2 (T1 sensor), PLC3 (T2 sensor) |
| **Duration** | Iterations 290-390 (100 iterations) |
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

3. **Recovery**: After minimum guard period (10 iterations), when T1 readings 
   start varying again (variance > 0.2):
   - Return to normal sensor-based control

### Algorithm Location
```
ScadaAlgos/
├── Scada_P1_Algo.py    # Guard algorithm for pump P1
└── ScadaData/
    ├── scada_data.csv       # Historical SCADA readings
    └── GuardRoutineState.txt # Guard state persistence
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
# Clean previous state before running
rm -f examples/EdenTown/Scada_Case/3_DoS_WithGuard/ScadaAlgos/ScadaData/*

# Run simulation
wacsim examples/EdenTown/Scada_Case/3_DoS_WithGuard/config.yaml
```

**Important**: Delete the `ScadaData/` contents before each run to reset the 
guard state.

## Expected Results

| Phase | Iterations | P1 Behavior | T1 Level |
|-------|------------|-------------|----------|
| Normal | 0-289 | Sensor-based control | Oscillates 5-7m |
| Attack | 290-390 | Historical median cycling | Maintains ~5-7m range |
| Recovery | 391-500 | Returns to sensor-based | Stabilizes |

## Guard Algorithm State Machine

```
                    ┌─────────────┐
                    │   NORMAL    │
                    │  (Sensors)  │
                    └──────┬──────┘
                           │
         DoS detected      │
         (T1 variance <0.1)│
                           ▼
                    ┌─────────────┐
                    │   GUARD     │◄────────────┐
                    │ (Medians)   │             │
                    └──────┬──────┘             │
                           │                    │
         Guard iter        │      Guard iter    │
         >= 10 AND         │      < 10 OR       │
         T1 variance >0.2  │      T1 variance   │
                           │      < 0.2         │
                           ▼                    │
                    ┌─────────────┐             │
                    │  RECOVERY   │─────────────┘
                    │  (Check)    │
                    └──────┬──────┘
                           │
         T1 variance >0.2  │
         (sensors working) │
                           ▼
                    ┌─────────────┐
                    │   NORMAL    │
                    │  (Sensors)  │
                    └─────────────┘
```

## Bug Fixes (v0.5.1.1)

The guard algorithm was updated to fix several issues:

### 1. False Teardown Detection
**Problem**: Teardown was triggering during normal pump cycling when T1 changed by >0.1m.

**Fix**: Changed teardown detection to require:
- Minimum 10 iterations in guard mode first
- T1 variance > 0.2 (double threshold) to confirm sensors are working

### 2. Guard State Reset Loop
**Problem**: Teardown check ran before DoS check, causing constant state resets.

**Fix**: Check DoS FIRST, then only check teardown if:
- We're currently in guard mode
- Minimum guard iterations have passed

### 3. Improved State Tracking
**Added**: `guard_iteration` counter in state file to track how long we've been in guard mode.

## Comparison with Scenario 2 (No Guard)

Without the guard algorithm, the pump maintains its last state throughout 
the attack, potentially causing:
- Tank overflow (if pump was ON)
- Tank empty (if pump was OFF)
- Service disruption

The guard algorithm prevents these issues by intelligently cycling the pump.
