# Custom Algorithms Without INP File Controls

## Overview

This directory contains examples demonstrating the **new feature** that allows you to create custom control algorithms for pumps and valves **without needing to define control rules in the INP file's `[CONTROLS]` section**.

### What Changed?

**Before (Old Approach):**
1. Define a control rule in your INP file's `[CONTROLS]` section
2. Specify a custom algorithm in the YAML configuration
3. The custom algorithm would override the INP control rule

**Now (New Feature):**
1. ✅ Just specify the custom algorithm in the YAML configuration
2. ✅ Optionally specify a `dependent` sensor if your algorithm needs one
3. ✅ WaCSim automatically creates the necessary control infrastructure
4. ✅ **Backward compatible** - the old approach still works!

## Files in This Directory

- `example_custom_algorithm_no_inp.yaml` - Example configuration showing the new syntax
- `custom_algos/pump_controller.py` - Example algorithm with a dependent sensor
- `custom_algos/time_based_pump.py` - Example algorithm without a dependent sensor

## Quick Start

### Example 1: Algorithm with Dependent Sensor

If your custom algorithm needs to read a specific sensor (e.g., a tank level):

```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: custom_algos/pump_controller.py
      dependent: T1  # Tank sensor the algorithm will read
```

**What WaCSim does automatically:**
- Creates a synthetic control for actuator `P1`
- Registers sensor `T1` as a dependent sensor for PLC1
- Executes your custom algorithm at every simulation iteration
- Makes the sensor value available in `plc_dict` and `plc_cache`

**Your Python algorithm** (`pump_controller.py`):
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    # Access the dependent sensor
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Implement your control logic
    if tank_level < 2.0:
        return "open"  # Turn pump on
    elif tank_level > 4.0:
        return "closed"  # Turn pump off
    else:
        return "open" if plc_dict.get(('P1', 1), 0) == 1 else "closed"
```

### Example 2: Algorithm without Dependent Sensor

If your algorithm uses time-based logic or multiple sensors:

```yaml
- name: PLC2
  actuators:
    - name: P2
      decision_maker: custom_algos/time_based_pump.py
      # No 'dependent' field - algorithm handles its own data access
```

**Your Python algorithm** (`time_based_pump.py`):
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    # Access multiple sensors from plc_dict
    tank1 = plc_dict.get(('T1', 1), 0.0)
    tank2 = plc_dict.get(('T2', 1), 0.0)
    
    # Implement complex logic
    if tank1 < 3.0 and tank2 > 5.0:
        return "open"
    else:
        return "closed"
```

## How It Works Internally

When WaCSim processes your configuration:

1. **Config Parser** validates the YAML and accepts the optional `dependent` field
2. **Input Parser** reads the INP file and extracts existing controls
3. **Synthetic Control Generation**:
   - For each actuator with a custom algorithm (`.py` file path)
   - If no INP control exists for that actuator
   - Creates a synthetic control:
     - **With dependent**: Creates an ABOVE control with unreachable threshold
     - **Without dependent**: Creates a TIME control at time 0
4. **Dependent Registration**: Adds specified dependent sensors to PLC's sensor list
5. **Runtime**: Generic PLC/SCADA executes custom algorithms at every iteration

## Backward Compatibility

The original workflow is fully supported:

### Old Approach (Still Works)

**INP File (`minitown_map.inp`):**
```
[CONTROLS]
LINK P1 OPEN IF NODE T1 BELOW 2.0
LINK P1 CLOSED IF NODE T1 ABOVE 4.0
```

**YAML Config:**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: custom_algos/my_algo.py
```

This works exactly as before - the INP controls are parsed, and your custom algorithm can override them.

## Use Cases

### 1. Simple Tank Level Control
Use a dependent sensor to monitor tank level and control a pump:
```yaml
- name: P1
  decision_maker: tank_controller.py
  dependent: T101
```

### 2. Multi-Sensor Logic
Access multiple sensors without specifying dependents:
```yaml
- name: P2
  decision_maker: multi_sensor_controller.py
  # No dependent - accesses T1, T2, T3 from plc_dict
```

### 3. Machine Learning Control
Implement ML-based control without INP rules:
```yaml
- name: P3
  decision_maker: ml_controller.py
  dependent: T201
```

### 4. Time-Based Scheduling
Implement schedules without INP TIME controls:
```yaml
- name: P4
  decision_maker: scheduler.py
  # No dependent - uses time/iteration for decisions
```

## Advanced Features

### Return Values

Your `AlgoRun` function can return:

1. **Simple string**: `"open"`, `"closed"`, `"rule"`, or `"scada"`
   ```python
   return "open"
   ```

2. **Tuple with skip flag**: `(result, skip_flag)`
   ```python
   return ("closed", True)  # Skip further processing of this actuator
   ```

### Accessing Data

**PLC Mode (`plccontrol`, `hybridcontrol`):**
- `plc_cache`: Values from other PLCs
- `plc_dict`: Local sensor/actuator values
- `scada_cache`: SCADA commands (hybrid mode only)

**SCADA Mode (`scadacontrol`, `hybridcontrol`):**
- `cache_dict`: All sensor/actuator values from all PLCs

### Example: Skip Flag Usage

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    tank = plc_dict.get(('T1', 1), 0.0)
    
    if tank < 2.0:
        # Turn on and skip further processing
        return ("open", True)
    elif tank > 4.0:
        # Turn off and skip further processing
        return ("closed", True)
    else:
        # Let other controls handle it
        return "rule"
```

## Testing Your Configuration

1. Create your custom algorithm Python file
2. Update your decision_maker YAML with the new syntax
3. Reference the decision_maker YAML in your main config:
   ```yaml
   mode: plccontrol
   decision_maker_per_plc: !include example_custom_algorithm_no_inp.yaml
   ```
4. Run WaCSim as usual - no INP file changes needed!

## Troubleshooting

### "Tag does not exist" error
- Make sure the `dependent` sensor name matches a sensor in your PLC's `sensors` list or is accessible via network
- Or omit the `dependent` field and access sensors directly in your algorithm

### Algorithm not executing
- Verify the path to your `.py` file is correct (relative to config YAML)
- Check that `AlgoRun` function is defined with correct signature
- Look for errors in the WaCSim logs

### Sensor value is always 0
- Ensure the dependent sensor is actually connected to the PLC
- Verify sensor exists in the INP file's JUNCTIONS or TANKS section
- Check that the sensor is listed in the PLC's `sensors` field

## Documentation

For more details, see:
- `doc/CustomAlgorithm.rst` - Complete custom algorithm documentation
- `doc/experiment_config_docs.rst` - Configuration file reference
- `examples/` - More example configurations

## Summary

This new feature makes it easier to:
- ✅ Experiment with custom control logic
- ✅ Prototype without modifying INP files
- ✅ Iterate faster on control algorithms
- ✅ Keep control logic separate from network topology
- ✅ Maintain cleaner, more modular configurations

**And it's fully backward compatible with existing configurations!**

