# EdenTown Odd/Even Custom Algorithm Example

## Overview

This example demonstrates the **NEW FEATURE** that allows custom algorithms to control actuators **WITHOUT needing to define control rules in the INP file's `[CONTROLS]` section**.

## What This Example Does

This configuration controls two pumps (P1 and P2) based on whether their associated tank levels are odd or even:

- **Pump P1** (controlled by PLC4):
  - Reads tank T1 level
  - **ON (open)** if T1 level is EVEN (e.g., 2, 4, 6 meters)
  - **OFF (closed)** if T1 level is ODD (e.g., 1, 3, 5 meters)

- **Pump P2** (controlled by PLC1):
  - Reads tank T2 level
  - **ON (open)** if T2 level is EVEN
  - **OFF (closed)** if T2 level is ODD

## Key Files

1. **EdenTown_OddEven_config.yaml** - Main configuration file
2. **EdenTown_OddEven_decision_plc.yaml** - Decision maker configuration with `dependent` fields
3. **CustomAlgos/OddEven_P1_Algo.py** - Custom algorithm for pump P1
4. **CustomAlgos/OddEven_P2_Algo.py** - Custom algorithm for pump P2

## The New Feature in Action

### Configuration (EdenTown_OddEven_decision_plc.yaml)

```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P1_Algo.py
      dependent: T1  # NEW: Specifies the dependent sensor
```

**What happens automatically:**
1. ✅ WaCSim creates a synthetic control for P1 (no INP control needed!)
2. ✅ T1 is registered as a dependent sensor for PLC4
3. ✅ The custom algorithm executes at every iteration
4. ✅ Tank level is available in the algorithm's input dictionaries

### Custom Algorithm (OddEven_P1_Algo.py)

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    # Get tank T1 level - automatically available!
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Convert to integer
    tank_level_int = int(tank_level)
    
    # Check if even or odd
    is_even = (tank_level_int % 2 == 0)
    
    # Return decision
    if is_even:
        return "open"   # Even -> Pump ON
    else:
        return "closed"  # Odd -> Pump OFF
```

## How to Run

```bash
cd /Users/stavcohn/Desktop/Personal/wcasim/WaCSim-master
wacsim examples/EdenTown/OddEven_CustomAlgo_Example/EdenTown_OddEven_config.yaml
```

## Expected Behavior

As the simulation runs:

1. Tank levels (T1 and T2) will change based on water flow
2. When a tank level crosses from even to odd (e.g., 4.9 → 3.1), the pump turns OFF
3. When a tank level crosses from odd to even (e.g., 3.9 → 4.1), the pump turns ON
4. You can observe this in the output CSV files:
   - `OddEven_Demo_Output/PLC4_values.csv` - shows P1 states and T1 levels
   - `OddEven_Demo_Output/PLC1_values.csv` - shows P2 states
   - Tank levels visible in PLC2 and PLC3 values (they have the sensors)

## Verification

To verify the new feature is working:

1. **Check the logs** - Look for messages like:
   ```
   Created synthetic ABOVE control for actuator 'P1' in PLC 'PLC4' with dependent 'T1' for custom algorithm
   ```

2. **Check output CSV** - Open `OddEven_Demo_Output/PLC4_values.csv`:
   - Look at the T1 column (tank level)
   - Look at the P1 column (pump state: 0=off, 1=on)
   - Verify: When T1 integer value is even, P1 should be 1
   - Verify: When T1 integer value is odd, P1 should be 0

3. **No INP Controls Needed** - Check `EdenTown.inp`:
   - You'll see there are NO `[CONTROLS]` entries for P1 or P2 using T1 or T2
   - The custom algorithms work without them!

## Comparison with Original

### Original Approach (EdenTown_decision_plc.yaml)
- Required INP file controls
- Algorithm overrides INP logic
- More setup needed

### New Approach (EdenTown_OddEven_decision_plc.yaml)
- ✅ No INP controls required for P1 and P2
- ✅ Just specify `dependent: T1` or `dependent: T2`
- ✅ Cleaner configuration
- ✅ Faster prototyping

## Backward Compatibility

Note that V4 and V5 still use the original approach in this example:
```yaml
- name: PLC2
  actuators:
    - name: V5
      decision_maker: examples/EdenTown/PLC_Case/PLCAlgos/V5_Algo.py
      # No 'dependent' field - uses INP controls
```

This shows that both approaches work together seamlessly!

## Key Takeaways

1. **No INP modifications needed** - Add custom algorithms without touching INP files
2. **Simple sensor specification** - Use `dependent: SENSOR_NAME` 
3. **Automatic infrastructure** - WaCSim handles control creation and sensor registration
4. **Full backward compatibility** - Mix new and old approaches freely
5. **Faster development** - Prototype control logic without complex INP editing

## Next Steps

Try modifying the algorithm:
- Change the logic (e.g., use different thresholds instead of odd/even)
- Add more sensors to the algorithm
- Implement more complex decision logic
- Use machine learning models
- Log data to external files

The new feature makes all of this easier!

