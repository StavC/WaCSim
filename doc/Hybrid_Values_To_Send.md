# Hybrid_Values_To_Send Feature

## Overview

The `Hybrid_Values_To_Send` feature allows explicit configuration of which sensor values SCADA should send to PLCs in **hybrid mode**. This replaces the previous implicit mechanism that relied on control dependencies.

## When to Use

Use this feature when:
- Running in `hybridcontrol` mode
- You want PLCs to receive specific sensor values from SCADA
- You need PLC algorithms to compare local readings with SCADA's view (e.g., for MitM detection)

## Configuration

Add `Hybrid_Values_To_Send` to your `decision_maker_per_scadacommand` configuration:

```yaml
# decision_scada.yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: ScadaAlgos/P1_Algo.py
      Hybrid_Values_To_Send: [T1, J1, T2]  # Sensors to send to PLC
```

### Field Description

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Hybrid_Values_To_Send` | list of strings | No | Sensor names that SCADA will send to the PLC with an "S" suffix |

## How It Works

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ SCADA Cache                                                      │
│   T1: 15.2, J1: 0.5, T2: 18.7, ...                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCADA sends (based on Hybrid_Values_To_Send: [T1, J1])          │
│   T1S = 15.2                                                     │
│   J1S = 0.5                                                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ PLC scadaCache                                                   │
│   ScadaCommand_P1: 1.0    ← SCADA's actuator decision           │
│   T1S: 15.2               ← Sensor value from SCADA             │
│   J1S: 0.5                ← Sensor value from SCADA             │
└─────────────────────────────────────────────────────────────────┘
```

### Tag Naming Convention

- Original sensor: `T1`
- SCADA-sent value: `T1S` (with "S" suffix)

This allows PLC algorithms to distinguish between:
- Local sensor readings (direct from physical process)
- SCADA's view of the sensor (may differ if MitM attack exists)

## PLC Algorithm Access

In your PLC algorithm, access SCADA-sent values from `scada_cache`:

```python
def AlgoRun(cache, local_sensors, scada_cache, control):
    # Local sensor reading (direct from physical process)
    local_T1 = local_sensors.get('T1', 0)
    
    # SCADA's view of the same sensor
    scada_T1 = scada_cache.get('T1S', 0)
    
    # Compare for anomaly detection
    if scada_T1 is not None and abs(local_T1 - scada_T1) > 0.5:
        # Significant difference detected - possible MitM attack!
        return 'closed'  # Safe action
    
    # Normal operation
    if local_T1 < 10:
        return 'open'
    return 'closed'
```

## Example Use Cases

### 1. MitM Attack Detection

Compare local sensor readings with SCADA's view to detect man-in-the-middle attacks on the network.

```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: guard_algorithm.py
      Hybrid_Values_To_Send: [T1]  # PLC compares local T1 with T1S from SCADA
```

### 2. Consensus-Based Control

PLC uses both local and SCADA data to make more robust decisions.

```yaml
- name: PLC2
  actuators:
    - name: V5
      decision_maker: consensus_controller.py
      Hybrid_Values_To_Send: [T1, T2, J1, J2]  # Multiple sensors for consensus
```

### 3. Distributed Validation

SCADA sends its computed setpoints, PLC validates before applying.

```yaml
- name: PLC3
  actuators:
    - name: V4
      decision_maker: validator.py
      Hybrid_Values_To_Send: [T2]  # Validate SCADA's decision against local T2
```

## Comparison with `dependents`

| Feature | `dependents` | `Hybrid_Values_To_Send` |
|---------|--------------|-------------------------|
| Purpose | Ensure sensors are collected by SCADA | Specify which values SCADA sends to PLC |
| Mode | SCADA and Hybrid | Hybrid only |
| Direction | PLC → SCADA (collection) | SCADA → PLC (sending) |
| Tag suffix | None | "S" suffix (e.g., T1S) |

**Note**: You may still need `dependents` if the sensors you want to send are not already in any PLC's sensor list. `dependents` ensures SCADA collects the data; `Hybrid_Values_To_Send` ensures SCADA sends it to PLCs.

## Complete Example

### Config File (config.yaml)

```yaml
inp_file: network.inp
plcs: !include plcs.yaml
output_path: output
mode: hybridcontrol  # Must be hybridcontrol to use Hybrid_Values_To_Send
decision_maker_per_scadacommand: !include decision_scada.yaml
```

### Decision SCADA Config (decision_scada.yaml)

```yaml
- name: PLC1
  actuators:
    - name: P2
      decision_maker: rule  # Use INP rules

- name: PLC4
  actuators:
    - name: P1
      decision_maker: ScadaAlgos/guard.py
      Hybrid_Values_To_Send: [T1, J1]
```

### Guard Algorithm (guard.py)

```python
def AlgoRun(cache, local_sensors, scada_cache, control):
    """
    Guard algorithm that detects sensor discrepancies.
    """
    local_T1 = local_sensors.get('T1', 0)
    scada_T1 = scada_cache.get('T1S')
    
    # Check for sensor tampering
    if scada_T1 is not None:
        discrepancy = abs(local_T1 - scada_T1)
        if discrepancy > 1.0:
            # Log alert and take safe action
            return 'closed'
    
    # Normal control logic
    if local_T1 < 10:
        return 'open'
    elif local_T1 > 20:
        return 'closed'
    
    return 'scada'  # Follow SCADA's decision
```

## Troubleshooting

### Values Not Appearing in scadaCache

1. Ensure `mode: hybridcontrol` in your config
2. Verify sensor names in `Hybrid_Values_To_Send` match exactly (case-sensitive)
3. Check that sensors exist in some PLC's sensor list (or add them via `dependents`)

### KeyError When Accessing Sensor

If your algorithm throws a KeyError for a sensor:
- Use `.get()` method with a default value: `scada_cache.get('T1S', None)`
- Verify the sensor is listed in `Hybrid_Values_To_Send`
