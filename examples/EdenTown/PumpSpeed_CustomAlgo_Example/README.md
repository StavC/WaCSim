# Pump Speed Control Example 🚀

## Overview

This example demonstrates **variable speed pump control** in WaCSim. Instead of simple on/off control, the custom algorithms return numeric speed values (0.0 to 2.0) that are passed directly to EPANET's pump speed multiplier.

## What's Special

- **Variable Speed**: Pumps can run at any speed from 0% to 200%
- **Numeric Returns**: Custom algorithms return `float` values, not just "open"/"closed"
- **EPANET Integration**: Speed values are applied via EPANET's `SETTING` property
- **Cycling Pattern**: Speed increments by 0.1 every iteration, cycling back to 0.0

## Speed Values

| Value | Meaning | Effect |
|-------|---------|--------|
| `0.0` | Pump OFF | No flow |
| `0.5` | 50% speed | Half flow |
| `1.0` | 100% speed | Normal flow |
| `1.5` | 150% speed | 50% more flow |
| `2.0` | 200% speed | Maximum flow |

## Algorithm Behavior

The custom algorithms cycle through speed values:

```
Iteration 1:  Speed = 0.0 (OFF)
Iteration 2:  Speed = 0.1
Iteration 3:  Speed = 0.2
...
Iteration 15: Speed = 1.4
Iteration 16: Speed = 1.5 (Maximum for this demo)
Iteration 17: Speed = 0.0 (Reset - cycle begins again)
```

## Files

```
PumpSpeed_CustomAlgo_Example/
├── EdenTown_PumpSpeed_config.yaml      # Main config
├── EdenTown_PumpSpeed_decision_plc.yaml # Decision maker config
├── README.md                            # This file
└── CustomAlgos/
    ├── PumpSpeed_P1_Algo.py            # Speed control for P1
    └── PumpSpeed_P2_Algo.py            # Speed control for P2
```

## How to Run

```bash
cd /path/to/WaCSim
wacsim examples/EdenTown/PumpSpeed_CustomAlgo_Example/EdenTown_PumpSpeed_config.yaml
```

## State Files

The algorithms maintain state in JSON files:
- `CustomAlgos/P1_speed_state.json`
- `CustomAlgos/P2_speed_state.json`

These files track the current speed for each pump. Delete them to reset the speed to 0.0.

## Implementation Details

### Custom Algorithm Return Value

The key difference from binary control is the return value:

```python
# Binary control (old way)
return "open"    # Pump ON at full speed
return "closed"  # Pump OFF

# Speed control (new way)
return 0.0   # Pump OFF
return 0.5   # Pump at 50% speed
return 1.0   # Pump at 100% speed
return 1.5   # Pump at 150% speed
```

### EPANET Integration

WaCSim automatically detects numeric return values and uses EPANET's `SETTING` property instead of `STATUS`:

```python
# In physical_process.py
if not math.isclose(control['value'], 1) and not math.isclose(control['value'], 0):
    # Numeric value - use SETTING for pump speed
    en.setlinkvalue(ph=self.proj, index=idx, property=en.SETTING, value=control['value'])
else:
    # Binary value - use STATUS for on/off
    en.setlinkvalue(ph=self.proj, index=idx, property=en.STATUS, value=control['value'])
```

## Expected Results

Watch the output CSV file to see:
1. **P1F** and **P2F** (pump flow) varying with speed
2. Flow roughly proportional to speed: 150% speed ≈ 150% flow
3. Tank levels fluctuating based on pump output

## Troubleshooting

### Speed Not Changing?
1. Delete the state JSON files and re-run
2. Check log output for custom algorithm execution
3. Verify the decision_maker path in YAML is correct

### Pump Always OFF?
1. Ensure `physical_process.py` uses `float()` instead of `int()` for reading values
2. Check that `control.py` passes through numeric values (not converting to "closed")

## Backward Compatibility

This feature is fully backward compatible:
- `"open"` and `"closed"` strings still work
- Existing examples continue to function
- Speed control is opt-in via numeric return values

