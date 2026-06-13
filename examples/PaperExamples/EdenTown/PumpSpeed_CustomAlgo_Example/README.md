# Intelligent Pump Speed Control Example 🚀

## Overview

This example demonstrates **intelligent variable speed pump control** in WaCSim. Instead of simple on/off control, the pump speed automatically adjusts based on tank water level - providing more realistic and energy-efficient operation.

## What's Special

- **Tank-Level Dependent**: Pump speed adjusts automatically based on tank level
- **Energy Efficient**: Slower pump speeds when tank is filling up
- **Realistic Control**: More like real-world variable frequency drives (VFDs)
- **Numeric Returns**: Custom algorithms return `float` values (0.0 to 2.0)

## Speed Logic

The pump speed is calculated based on the monitored tank level:

| Tank Level | Speed | Meaning |
|-----------|-------|---------|
| `< 2.0m` | `1.5` (150%) | URGENT - fill fast! |
| `< 4.0m` | `1.2` (120%) | Tank low - pump faster |
| `< 6.0m` | `1.0` (100%) | Normal operation |
| `< 8.0m` | `0.5` (50%) | Tank filling - slow down |
| `>= 8.0m` | `0.0` (OFF) | Tank full - save energy |

## Benefits Over On/Off Control

1. **Energy Savings**: Running at 50% speed uses ~12.5% of full-speed energy (power ∝ speed³)
2. **Reduced Water Hammer**: Gradual speed changes reduce pressure surges
3. **Extended Equipment Life**: Fewer start/stop cycles reduce mechanical wear
4. **Better Level Control**: More precise tank level maintenance

## Files

```
PumpSpeed_CustomAlgo_Example/
├── EdenTown_PumpSpeed_config.yaml      # Main config
├── EdenTown_PumpSpeed_decision_plc.yaml # Decision maker config with dependents
├── README.md                            # This file
└── CustomAlgos/
    ├── PumpSpeed_P1_Algo.py            # P1 speed based on T1 level
    └── PumpSpeed_P2_Algo.py            # P2 speed based on T2 level
```

## How to Run

```bash
cd /path/to/WaCSim
wacsim examples/EdenTown/PumpSpeed_CustomAlgo_Example/EdenTown_PumpSpeed_config.yaml
```

## CSV Output

The results CSV now includes pump speed in addition to flow and status:

| Column | Description |
|--------|-------------|
| `P1_FLOW` | Pump P1 flow rate |
| `P1_STATUS` | Pump P1 on/off status |
| `P1_SPEED` | **NEW** Pump P1 speed setting (0.0-2.0) |

## Configuration: Dependents

The `dependents` field in the YAML config registers which sensors the custom algorithm needs:

```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: .../PumpSpeed_P1_Algo.py
      dependents: [T1]  # Tank T1 level needed for speed calculation
```

## Algorithm Example

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    # Get tank level
    tank_level = plc_dict.get(('T1', 1), 3.0)
    
    # Calculate speed based on level
    if tank_level < 2.0:
        return 1.5  # 150% - urgent fill
    elif tank_level < 4.0:
        return 1.2  # 120% - fill faster
    elif tank_level < 6.0:
        return 1.0  # 100% - normal
    elif tank_level < 8.0:
        return 0.5  # 50% - slow down
    else:
        return 0.0  # OFF - tank full
```

## State Files

The algorithms track state for debugging:
- `CustomAlgos/P1_speed_state.json`
- `CustomAlgos/P2_speed_state.json`

Example state file content:
```json
{
  "tank_level": 4.5,
  "speed": 1.0,
  "iteration_count": 42
}
```

## Pump Curve Considerations

⚠️ **Important**: When using variable speed pumps, the pump curve matters!

The H1 curve in EdenTownBasic.inp:
- At 0% speed: No flow, no head
- At 50% speed: Head scales by (0.5)² = 25% of rated head
- At 150% speed: Head scales by (1.5)² = 225% of rated head

Make sure the pump can overcome system head at all operating speeds. A pump at 50% speed delivers much less head than at full speed, which may not overcome static head differences in the system.

## Troubleshooting

### Pump Flow is Zero at Low Speeds?
The pump may not overcome system head at reduced speed. Either:
1. Increase minimum speed threshold
2. Use a pump curve with higher shutoff head
3. Reduce static head differences in the network

### Tank Level Not Found?
1. Check the `dependents` list includes the tank sensor
2. Verify the tank sensor is assigned to a PLC in `EdenTown_plc.yaml`
3. Check the sensor name matches exactly (case-sensitive)

## Backward Compatibility

This feature is fully backward compatible:
- `"open"` and `"closed"` strings still work
- Existing on/off examples continue to function
- Speed control is opt-in via numeric return values
