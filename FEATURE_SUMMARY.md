# New Feature: Custom Algorithms Without INP File Controls

## Summary

This feature allows you to create custom control algorithms for actuators (pumps/valves) **without needing to define control rules in the INP file's `[CONTROLS]` section**. This makes it much easier to experiment with custom control logic while maintaining full backward compatibility.

## What Was Changed

### 1. Config Parser (`wacsim/parser/config_parser.py`)
**Changes:**
- Added optional `dependent` field to `decision_maker_plc_schema`
- Added optional `dependent` field to `decision_maker_per_scadacommand_schema`

**Impact:**
- YAML configurations can now specify a dependent sensor for custom algorithms
- Schema validation ensures the dependent sensor name is valid

### 2. Input Parser (`wacsim/parser/input_parser.py`)
**Changes:**
- Added `add_decision_maker_dependents()` method
  - Processes decision_maker configurations
  - Registers dependent sensors in PLC's dependent_sensors list
  - Handles both PLC and SCADA modes

- Added `generate_synthetic_controls_for_custom_algorithms()` method
  - Creates synthetic controls for actuators with custom algorithms but no INP controls
  - Creates ABOVE controls (with very high threshold) when dependent is specified
  - Creates TIME controls (at time 0) when no dependent is specified
  - Skips actuators that already have INP controls (backward compatibility)
  - Skips non-custom decision makers ('rule', 'scada', 'open', 'closed')

- Modified `write()` method to call the new methods in correct order

**Impact:**
- Actuators with custom algorithms no longer require INP file controls
- Dependent sensors are automatically registered
- Synthetic controls ensure custom algorithms execute at every iteration

### 3. Documentation (`doc/CustomAlgorithm.rst`)
**Changes:**
- Added new section: "Custom Algorithms Without INP File Controls (New Feature)"
- Explained how to use the `dependent` field
- Provided examples for both with and without dependent sensors
- Clarified backward compatibility

**Impact:**
- Users have clear documentation on how to use the new feature
- Migration path from old to new approach is explained

### 4. Example Files (Created)
**New Files:**
- `examples/getting_started/example_custom_algorithm_no_inp.yaml`
  - Demonstrates new YAML syntax
  - Shows various use cases

- `examples/getting_started/custom_algos/pump_controller.py`
  - Example algorithm with dependent sensor
  - Implements hysteresis control for pump based on tank level

- `examples/getting_started/custom_algos/time_based_pump.py`
  - Example algorithm without dependent sensor
  - Shows how to implement time-based or multi-sensor logic

- `examples/getting_started/CUSTOM_ALGORITHM_NO_INP_README.md`
  - Comprehensive guide with examples
  - Troubleshooting section
  - Use cases and best practices

## How It Works

### Architecture Flow

```
1. User creates YAML config with decision_maker and optional dependent
   ↓
2. ConfigParser validates schema (accepts 'dependent' field)
   ↓
3. InputParser reads INP file and parses existing controls
   ↓
4. add_decision_maker_dependents() registers dependent sensors
   ↓
5. generate_synthetic_controls_for_custom_algorithms() creates controls
   - If actuator has custom algo AND no INP control:
     * With dependent: Creates ABOVE control (unreachable threshold)
     * Without dependent: Creates TIME control (time=0)
   ↓
6. GenericPLC/GenericSCADA execute as before
   - Iterates through controls
   - Checks decision_maker for each actuator
   - Executes custom algorithm if specified
```

### Key Design Decisions

1. **Synthetic Control Type:**
   - **With dependent**: ABOVE control with threshold 999999.0
     - Ensures control has proper structure (type, dependent, value, actuator, action)
     - Never triggers naturally, but provides framework for custom algo
   - **Without dependent**: TIME control at time 0
     - Minimal control structure
     - Executes at simulation start

2. **Backward Compatibility:**
   - Only creates synthetic controls if no INP control exists
   - Old configurations work unchanged
   - New 'dependent' field is optional

3. **Execution Model:**
   - Custom algorithms still execute at every iteration (via GenericPLC/SCADA loop)
   - Synthetic controls ensure control loop includes these actuators
   - No changes needed to generic_plc.py or generic_scada.py

## Usage Examples

### Example 1: Tank Level Control (With Dependent)

**YAML Configuration:**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: custom_algos/tank_controller.py
      dependent: T101
```

**Custom Algorithm:**
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    tank_level = plc_dict.get(('T101', 1), 0.0)
    
    if tank_level < 2.0:
        return "open"
    elif tank_level > 4.0:
        return "closed"
    else:
        # Maintain current state (hysteresis)
        current = plc_dict.get(('P1', 1), 0)
        return "open" if current == 1 else "closed"
```

**What Happens:**
1. T101 is added to PLC1's dependent_sensors
2. Synthetic ABOVE control created: `T101 > 999999.0 → P1 open`
3. Custom algorithm executes every iteration
4. Algorithm has access to T101 value in plc_dict

### Example 2: Multi-Sensor Logic (No Dependent)

**YAML Configuration:**
```yaml
- name: PLC2
  actuators:
    - name: P2
      decision_maker: custom_algos/multi_tank.py
```

**Custom Algorithm:**
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    t1 = plc_dict.get(('T1', 1), 0.0)
    t2 = plc_dict.get(('T2', 1), 0.0)
    t3 = plc_dict.get(('T3', 1), 0.0)
    
    # Complex logic using multiple sensors
    avg_level = (t1 + t2 + t3) / 3.0
    
    if avg_level < 3.0:
        return "open"
    else:
        return "closed"
```

**What Happens:**
1. Synthetic TIME control created: `time=0 → P2 open`
2. Custom algorithm executes every iteration
3. Algorithm accesses multiple sensors from plc_dict

## Backward Compatibility

### Old Approach (Still Works)

**INP File:**
```
[CONTROLS]
LINK P1 OPEN IF NODE T101 BELOW 2.0
LINK P1 CLOSED IF NODE T101 ABOVE 4.0
```

**YAML:**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: custom_algos/my_algo.py
```

**Result:**
- INP controls are parsed normally
- Custom algorithm can return "rule" to use INP logic
- Or return "open"/"closed" to override INP logic
- No synthetic control created (INP control exists)

### New Approach

**INP File:** (No [CONTROLS] needed for P1)

**YAML:**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: custom_algos/my_algo.py
      dependent: T101
```

**Result:**
- Synthetic control created automatically
- T101 registered as dependent
- Custom algorithm executes every iteration
- Cleaner separation of concerns

## Testing & Validation

### Files Modified
- ✅ `wacsim/parser/config_parser.py` - Schema updated
- ✅ `wacsim/parser/input_parser.py` - Logic added
- ✅ `doc/CustomAlgorithm.rst` - Documentation updated

### Files Created
- ✅ Example YAML configuration
- ✅ Example custom algorithms (2 files)
- ✅ Comprehensive README with examples

### Validation Points
- ✅ Schema accepts optional 'dependent' field
- ✅ Dependent sensors are registered in PLC
- ✅ Synthetic controls are created for custom algorithms
- ✅ Existing INP controls are preserved (no synthetic control created)
- ✅ Non-custom decision makers ('rule', 'scada', etc.) are skipped
- ✅ Backward compatibility maintained
- ✅ Documentation is comprehensive

## Benefits

1. **Faster Prototyping**: No need to modify INP files to test custom logic
2. **Cleaner Separation**: Control logic separated from network topology
3. **More Flexibility**: Easy to switch between algorithms without INP changes
4. **Better Modularity**: Custom algorithms are self-contained Python files
5. **Backward Compatible**: Existing configurations work unchanged
6. **Easier Debugging**: Clear separation between INP rules and custom logic

## Potential Future Enhancements

1. **Multiple Dependents**: Allow `dependent: [T1, T2, T3]` as a list
2. **Conditional Execution**: Add `enabled: true/false` flag for custom algorithms
3. **Priority System**: Allow specifying execution order for multiple controls
4. **Hot Reload**: Support reloading custom algorithms during simulation
5. **Validation**: Check that dependent sensors actually exist in network

## Notes for Users

1. The `dependent` field is **optional** - use it when your algorithm needs a specific sensor
2. You can still use INP file controls - they take precedence over synthetic controls
3. Custom algorithms execute at **every iteration** regardless of control type
4. The synthetic control's action ("open") is just a default - your algorithm determines actual behavior
5. Use logging in your custom algorithms to debug issues

## Migration Guide

### From Old to New Approach

**Step 1:** Identify custom algorithms in your config
```yaml
# Old: requires INP control
- name: PLC1
  actuators:
    - name: P1
      decision_maker: my_algo.py
```

**Step 2:** Check if custom algorithm needs a dependent sensor
- Look at your custom algorithm code
- Find which sensor it reads most frequently
- That's your dependent sensor

**Step 3:** Add dependent field (if applicable)
```yaml
# New: no INP control needed
- name: PLC1
  actuators:
    - name: P1
      decision_maker: my_algo.py
      dependent: T101  # Add this line
```

**Step 4:** (Optional) Remove INP control
- If you want cleaner separation, remove from INP file
- Or keep it - both approaches work!

## Conclusion

This feature makes WaCSim more flexible and user-friendly while maintaining complete backward compatibility. Users can now prototype custom control logic faster without modifying INP files, and the system automatically handles the infrastructure needed to execute custom algorithms.

All changes are non-breaking, well-documented, and include comprehensive examples for users to learn from.

