# EdenTown Stateful Alternating Pump Control Example

## Overview

This example demonstrates the **NEW FEATURE** that allows custom algorithms to control actuators **WITHOUT needing to define control rules in the INP file's `[CONTROLS]` section**. It showcases **stateful algorithms** that maintain state across iterations using JSON files.

## What This Example Does

This configuration controls two pumps (P1 and P2) with a simple alternating pattern:

- **Pump P1** (controlled by PLC4):
  - **5 iterations OPEN** (pump running)
  - **5 iterations CLOSED** (pump off)
  - **Repeat indefinitely**
  - State tracked in `CustomAlgos/P1_state.json`

- **Pump P2** (controlled by PLC1):
  - **5 iterations OPEN** (pump running)
  - **5 iterations CLOSED** (pump off)
  - **Repeat indefinitely**
  - State tracked in `CustomAlgos/P2_state.json`

## Key Files

1. **EdenTown_OddEven_config.yaml** - Main configuration file
2. **EdenTown_OddEven_decision_plc.yaml** - Decision maker configuration
3. **CustomAlgos/OddEven_P1_Algo.py** - Stateful custom algorithm for pump P1
4. **CustomAlgos/OddEven_P2_Algo.py** - Stateful custom algorithm for pump P2
5. **CustomAlgos/P1_state.json** - Auto-created JSON file tracking P1 state
6. **CustomAlgos/P2_state.json** - Auto-created JSON file tracking P2 state

## The New Feature in Action

### Configuration (EdenTown_OddEven_decision_plc.yaml)

```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P1_Algo.py
      dependents: []  # NEW: Empty list - no sensors needed for time-based control
```

**What happens automatically:**
1. ✅ WaCSim creates a synthetic TIME control for P1 (no INP control needed!)
2. ✅ No dependent sensors registered (algorithm doesn't need any)
3. ✅ The custom algorithm executes at every iteration
4. ✅ Algorithm maintains its own state in a JSON file

### Custom Algorithm (OddEven_P1_Algo.py)

```python
import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "P1_state.json")
ITERATIONS_PER_STATE = 5

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    # Load or initialize state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
    else:
        state = {"iteration": 1, "state": "open"}
    
    # Get current state
    current_iteration = state["iteration"]
    current_state = state["state"]
    
    # This iteration's action
    action = current_state
    
    # Increment and check if we need to toggle
    new_iteration = current_iteration + 1
    if new_iteration > ITERATIONS_PER_STATE:
        new_state = "closed" if current_state == "open" else "open"
        new_iteration = 1  # Reset counter
    else:
        new_state = current_state
    
    # Save updated state
    state = {"iteration": new_iteration, "state": new_state}
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    return action
```

### JSON State Files

During simulation, the algorithms create and update JSON files:

**P1_state.json** (example during execution):
```json
{
  "iteration": 3,
  "state": "open"
}
```

This means:
- Pump P1 is currently **OPEN**
- This is **iteration 3** of 5 in the current state
- After 2 more iterations, it will switch to **CLOSED**

## How to Run

```bash
cd /Users/stavcohn/Desktop/Personal/wcasim/WaCSim-master
wacsim examples/EdenTown/OddEven_CustomAlgo_Example/EdenTown_OddEven_config.yaml
```

## Expected Behavior

As the simulation runs:

1. **First 5 iterations**: P1 and P2 are both **OPEN**
2. **Next 5 iterations**: P1 and P2 are both **CLOSED**
3. **Pattern repeats** indefinitely
4. State persists in JSON files:
   - `CustomAlgos/P1_state.json`
   - `CustomAlgos/P2_state.json`
5. You can observe pump states in the output CSV files:
   - `OddEven_Demo_Output/PLC4_values.csv` - shows P1 states (0=closed, 1=open)
   - `OddEven_Demo_Output/PLC1_values.csv` - shows P2 states (0=closed, 1=open)

## Verification

To verify the new feature is working:

1. **Check the logs** - Look for messages like:
   ```
   PLC PLC4 executing custom algorithm for actuator P1 (script: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P1_Algo.py)
   ```

2. **Check JSON state files**:
   ```bash
   cat examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/P1_state.json
   ```
   You should see the iteration count and current state.

3. **Check output CSV** - Open `OddEven_Demo_Output/PLC4_values.csv`:
   - Look at the P1 column (pump state: 0=off, 1=on)
   - Count iterations: should be 5 consecutive 1s, then 5 consecutive 0s, repeat

4. **No INP Controls Needed** - Check `EdenTown.inp`:
   - There are NO `[CONTROLS]` entries for P1 or P2
   - The custom algorithms work without them!

## Comparison with Original

### Original Approach
- Required INP file controls
- Algorithm overrides INP logic
- More setup needed

### New Approach (This Example)
- ✅ **No INP controls** required for P1 and P2
- ✅ **No sensors needed** (time-based control)
- ✅ **Stateful** - maintains state in JSON files
- ✅ **Simple** - just specify `dependents: []`
- ✅ **Flexible** - algorithm has full control
- ✅ **Transparent** - state visible in JSON files

## Stateful Algorithm Benefits

This example demonstrates several advanced capabilities:

1. **State Persistence**: State survives across iterations via JSON files
2. **No Sensor Dependencies**: Pure time-based control without reading sensors
3. **Self-Contained**: Each algorithm manages its own state file
4. **Debuggable**: You can inspect/modify JSON files during runtime
5. **Simple Logic**: Easy to understand and modify

## Backward Compatibility

Note that V4 and V5 still use the original approach in this example:
```yaml
- name: PLC2
  actuators:
    - name: V5
      decision_maker: examples/EdenTown/PLC_Case/PLCAlgos/V5_Algo.py
      # No 'dependents' field - uses INP controls
```

This shows that both approaches work together seamlessly!

## Key Takeaways

1. **No INP modifications needed** - Add custom algorithms without touching INP files
2. **Optional sensor dependencies** - Use `dependents: []` for time-based control
3. **Stateful algorithms** - Persist data between iterations using files
4. **Automatic infrastructure** - WaCSim handles control creation automatically
5. **Full backward compatibility** - Mix new and old approaches freely
6. **Easy debugging** - Inspect JSON state files during simulation

## Modifying the Algorithm

Try these modifications:

### Change the timing pattern:
```python
ITERATIONS_PER_STATE = 10  # 10 on, 10 off
```

### Add more complex patterns:
```python
PATTERN = ["open", "open", "open", "closed", "open"]  # Custom sequence
```

### Add logging:
```python
with open("pump_log.txt", "a") as log:
    log.write(f"Iteration {current_iteration}: {action}\n")
```

### Read sensors (add to `dependents`):
```python
tank_level = plc_dict.get(('T1', 1), 0.0)
if tank_level > 5.0:
    return "closed"  # Override pattern if tank too full
```

## Next Steps

Explore other stateful algorithm possibilities:
- Time-of-day based control
- Learning algorithms that adapt over time
- Predictive maintenance based on accumulated runtime
- Complex finite state machines
- Integration with external data sources

The new feature makes all of this easier!
