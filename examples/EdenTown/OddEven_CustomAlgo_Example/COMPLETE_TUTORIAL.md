# Complete Tutorial: Custom Algorithms in WaCSim

## Table of Contents
1. [Introduction](#introduction)
2. [Two Approaches to Custom Algorithms](#two-approaches)
3. [Approach 1: Without INP Controls (NEW - Recommended)](#approach-1-without-inp-controls)
4. [Approach 2: With INP Controls (Traditional)](#approach-2-with-inp-controls)
5. [EdenTown Example Walkthrough](#edentown-example)
6. [Step-by-Step Implementation Guide](#step-by-step-guide)
7. [Advanced Topics](#advanced-topics)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

WaCSim allows you to implement **custom control algorithms** in Python to control pumps, valves, and other actuators in water distribution networks. This tutorial covers everything you need to know about creating and using custom algorithms.

### What Are Custom Algorithms?

Custom algorithms are Python scripts that make control decisions for actuators (pumps/valves) based on:
- Sensor readings (tank levels, pressures, flows)
- Time/iteration
- Historical data
- Machine learning models
- Any custom logic you can code

### Why Use Custom Algorithms?

- ✅ **Flexibility**: Implement any control logic you can code
- ✅ **Machine Learning**: Use ML models for intelligent control
- ✅ **Research**: Test novel control strategies
- ✅ **Real-world Logic**: Implement actual SCADA/PLC algorithms
- ✅ **Dynamic Behavior**: Adapt to changing conditions

---

## Two Approaches to Custom Algorithms

WaCSim supports **two approaches** for implementing custom algorithms:

### Approach 1: **Without INP Controls** (NEW ⭐ Recommended)
- **No INP file modification needed**
- Specify algorithm and sensors in YAML
- WaCSim automatically creates control infrastructure
- **Cleaner, faster, more intuitive**

### Approach 2: **With INP Controls** (Traditional)
- Define controls in INP file's `[CONTROLS]` section
- Custom algorithm overrides INP logic
- More setup required
- **Still fully supported for backward compatibility**

---

## Approach 1: Without INP Controls (NEW)

### Overview

With this approach, you **don't need to touch the INP file** at all. Just:
1. Write your Python algorithm
2. Specify it in the YAML configuration
3. List the sensors it needs (optional)

WaCSim automatically:
- Creates a synthetic TIME control at simulation start
- Registers your dependent sensors
- Executes your algorithm at every iteration

### YAML Configuration Format

```yaml
decision_maker_per_plc: !include decision_file.yaml
```

**In your decision file:**

```yaml
- name: PLC1
  actuators:
    - name: P1                           # Actuator name
      decision_maker: path/to/algo.py    # Your Python algorithm
      dependents: [T1, T2]               # Sensors it reads (optional)
```

### Python Algorithm Structure

Your algorithm must define an `AlgoRun` function:

**For PLC Mode (`plccontrol`, `hybridcontrol`):**

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Args:
        plc_cache: Dict of values from other PLCs via network
        plc_dict: Dict of local sensor/actuator values
        scada_cache: Dict of SCADA commands (hybrid mode only)
    
    Returns:
        str: "open", "closed", "rule", or "scada"
        tuple: (result, skip_flag) - optional
    """
    # Your logic here
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    if tank_level < 2.0:
        return "open"
    else:
        return "closed"
```

**For SCADA Mode (`scadacontrol`, `hybridcontrol`):**

```python
def AlgoRun(cache_dict):
    """
    Args:
        cache_dict: Dict of all sensor/actuator values from all PLCs
    
    Returns:
        str: "open", "closed", "rule", or "scada"
    """
    # Your logic here
    tank_level = cache_dict.get('T1', 0.0)
    
    if tank_level < 2.0:
        return "open"
    else:
        return "closed"
```

### Return Values

Your `AlgoRun` function can return:

| Return Value | Effect |
|--------------|--------|
| `"open"` | Set actuator to OPEN |
| `"closed"` | Set actuator to CLOSED |
| `"rule"` | Use INP file control rules (if they exist) |
| `"scada"` | Use SCADA command (in hybrid/scada mode) |
| `(result, True)` | Return result and skip further processing for this actuator |

### Complete Example

**File: `EdenTown_decision.yaml`**
```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P1_Algo.py
      dependents: [T1]
```

**File: `OddEven_P1_Algo.py`**
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Control pump P1 based on tank T1 level (odd/even)"""
    
    # Get tank level from local sensors
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Convert to integer
    tank_level_int = int(tank_level)
    
    # Even level -> Pump ON, Odd level -> Pump OFF
    if tank_level_int % 2 == 0:
        return "open"
    else:
        return "closed"
```

**File: `config.yaml`**
```yaml
inp_file: EdenTown.inp
plcs: !include EdenTown_plc.yaml
mode: plccontrol
decision_maker_per_plc: !include EdenTown_decision.yaml
iterations: 400
```

**Run it:**
```bash
wacsim config.yaml
```

That's it! No INP file changes needed.

### What Happens Internally?

1. **Schema Validation**: Validates your YAML configuration
2. **Sensor Registration**: Adds `T1` to PLC4's dependent sensors list
3. **Synthetic Control Creation**: Creates TIME control:
   ```
   LINK P1 OPEN AT TIME 0
   ```
4. **Runtime**: At every iteration:
   - PLC4 evaluates all controls
   - Finds P1 has custom algorithm
   - Loads and executes `OddEven_P1_Algo.py`
   - Applies the returned decision ("open" or "closed")

---

## Approach 2: With INP Controls (Traditional)

### Overview

This is the original approach where you:
1. Define control rules in INP file's `[CONTROLS]` section
2. Write custom algorithm to override/enhance those rules
3. Configure in YAML

### When to Use This Approach?

- ✅ You already have INP controls defined
- ✅ Your algorithm needs to "fall back" to INP rules sometimes
- ✅ Backward compatibility with existing configs
- ✅ You want explicit control rules visible in INP file

### INP File Setup

**File: `EdenTown.inp`**
```
[CONTROLS]
LINK P1 OPEN IF NODE T1 BELOW 2.0
LINK P1 CLOSED IF NODE T1 ABOVE 4.0
```

### YAML Configuration

Same as Approach 1, but the INP controls exist:

```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: path/to/algo.py
      dependents: [T1]  # Optional since T1 is in INP controls
```

### Python Algorithm

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Override INP controls with custom logic"""
    
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Custom logic
    if tank_level < 1.5:
        return "open"  # Override: more aggressive than INP
    elif tank_level > 4.5:
        return "closed"  # Override: more aggressive than INP
    else:
        return "rule"  # Fall back to INP control rules
```

### Differences from Approach 1

| Aspect | With INP Controls | Without INP Controls |
|--------|-------------------|----------------------|
| INP file | Must define `[CONTROLS]` | No changes needed |
| Synthetic control | Not created (uses INP) | Created at time 0 |
| Dependent sensors | Auto-detected from INP | Must specify in YAML |
| Return "rule" | Uses INP control logic | Does nothing (no INP rules) |
| Setup complexity | Higher | Lower |

---

## EdenTown Example Walkthrough

Let's walk through the **OddEven example** in detail.

### System Overview

**Network:** EdenTown water distribution system
- **2 Tanks**: T1, T2
- **2 Pumps**: P1, P2
- **4 PLCs**: PLC1, PLC2, PLC3, PLC4
- **Control Goal**: Turn pumps ON when tank level is EVEN, OFF when ODD

### File Structure

```
EdenTown/OddEven_CustomAlgo_Example/
├── EdenTown_OddEven_config.yaml        # Main config
├── EdenTown_OddEven_decision_plc.yaml  # Decision makers
├── CustomAlgos/
│   ├── OddEven_P1_Algo.py              # Algorithm for P1
│   └── OddEven_P2_Algo.py              # Algorithm for P2
└── (INP files referenced from ../PLC_Case/)
```

### Configuration Details

**1. Main Config** (`EdenTown_OddEven_config.yaml`):
```yaml
inp_file: ../PLC_Case/EdenTown.inp
output_path: OddEven_Demo_Output
iterations: 400
network_topology_type: complex
plcs: !include ../PLC_Case/EdenTown_plc.yaml
demand: pdd
log_level: info
demand_patterns: ../PLC_Case/demands_EdenTown.csv
mode: plccontrol
decision_maker_per_plc: !include EdenTown_OddEven_decision_plc.yaml
```

**2. Decision Makers** (`EdenTown_OddEven_decision_plc.yaml`):
```yaml
- name: PLC1
  actuators:
    - name: P2
      decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P2_Algo.py
      dependents: [T2]

- name: PLC4
  actuators:
    - name: P1
      decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P1_Algo.py
      dependents: [T1]
```

**3. P1 Algorithm** (`OddEven_P1_Algo.py`):
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Control pump P1 based on tank T1 level (odd/even).
    
    Logic:
    - Get T1 level from plc_dict (local sensors)
    - Convert to integer
    - If EVEN -> Pump ON
    - If ODD -> Pump OFF
    """
    # Get tank T1 level - automatically available because dependents: [T1]
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Convert to integer to check odd/even
    tank_level_int = int(tank_level)
    
    # Determine if odd or even
    is_even = (tank_level_int % 2 == 0)
    
    # Control logic
    if is_even:
        return "open"   # Even -> Pump ON
    else:
        return "closed"  # Odd -> Pump OFF
```

**4. P2 Algorithm** (`OddEven_P2_Algo.py`):
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Control pump P2 based on tank T2 level (odd/even).
    
    Note: T2 is connected to PLC2, not PLC1
    So we read it from plc_cache (network data)
    """
    # Get tank T2 level from network cache
    # (T2 is on PLC2, we're on PLC1)
    tank_level = plc_cache.get('T2', 0.0)
    
    # Convert to integer
    tank_level_int = int(tank_level)
    
    # Even -> ON, Odd -> OFF
    if tank_level_int % 2 == 0:
        return "open"
    else:
        return "closed"
```

### Key Points to Notice

1. **No INP Controls**: EdenTown.inp has no `[CONTROLS]` for P1 or P2
2. **Dependents List**: Each algorithm specifies which tank it reads
3. **Different Data Sources**:
   - P1 algo reads T1 from `plc_dict` (local - T1 is on PLC4)
   - P2 algo reads T2 from `plc_cache` (network - T2 is on PLC2)
4. **Simple Logic**: Just integer math (odd/even check)

### Running the Example

```bash
cd /path/to/WaCSim
wacsim examples/EdenTown/OddEven_CustomAlgo_Example/EdenTown_OddEven_config.yaml
```

**Expected Output:**
```
INFO: Created synthetic TIME control at time 0 for actuator 'P1' in PLC 'PLC4' with dependents ['T1']
INFO: Created synthetic TIME control at time 0 for actuator 'P2' in PLC 'PLC1' with dependents ['T2']
...
```

### Analyzing Results

**Check PLC4 values** (`OddEven_Demo_Output/PLC4_values.csv`):
```csv
iteration,timestamp,T1,P1
0,2024-01-01 00:00:00,3.051,0
1,2024-01-01 00:01:00,3.05,0
2,2024-01-01 00:02:00,3.04,0
3,2024-01-01 00:03:00,4.01,1
4,2024-01-01 00:04:00,4.02,1
```

**Verify the logic:**
- When T1 = 3.x (odd) → P1 = 0 (off) ✓
- When T1 = 4.x (even) → P1 = 1 (on) ✓

---

## Step-by-Step Implementation Guide

### Scenario: Control Pump Based on Tank Level

Let's implement a **hysteresis control** for pump P1 based on tank T1.

**Requirements:**
- Turn pump ON when T1 < 2.0 meters
- Turn pump OFF when T1 > 4.0 meters  
- Keep current state when 2.0 ≤ T1 ≤ 4.0

### Step 1: Write the Algorithm

**File: `tank_hysteresis.py`**
```python
#!/usr/bin/env python3
"""
Hysteresis control for pump based on tank level.
"""

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Implement hysteresis control.
    
    Args:
        plc_cache: Network sensor values
        plc_dict: Local sensor values
        scada_cache: SCADA commands (if hybrid mode)
    
    Returns:
        str: "open" or "closed"
    """
    # Get tank level
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Get current pump state
    pump_state = plc_dict.get(('P1', 1), 0)  # 0=off, 1=on
    
    # Hysteresis logic
    if tank_level < 2.0:
        # Tank too low - turn ON
        return "open"
    elif tank_level > 4.0:
        # Tank too high - turn OFF
        return "closed"
    else:
        # In hysteresis band - maintain state
        if pump_state == 0:
            return "closed"
        else:
            return "open"
```

### Step 2: Create Decision Maker Config

**File: `my_decision.yaml`**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: custom_algos/tank_hysteresis.py
      dependents: [T1]
```

### Step 3: Reference in Main Config

**File: `my_config.yaml`**
```yaml
inp_file: network.inp
plcs: !include plcs.yaml
mode: plccontrol
decision_maker_per_plc: !include my_decision.yaml
iterations: 500
output_path: output
```

### Step 4: Run

```bash
wacsim my_config.yaml
```

### Step 5: Verify

Check output CSV:
```python
import pandas as pd

df = pd.read_csv('output/PLC1_values.csv')

# Plot tank level and pump state
import matplotlib.pyplot as plt

fig, ax1 = plt.subplots()

ax1.plot(df['iteration'], df['T1'], 'b-', label='Tank Level')
ax1.set_xlabel('Iteration')
ax1.set_ylabel('Tank Level (m)', color='b')

ax2 = ax1.twinx()
ax2.plot(df['iteration'], df['P1'], 'r-', label='Pump State')
ax2.set_ylabel('Pump State', color='r')

plt.title('Hysteresis Control Verification')
plt.show()
```

---

## Advanced Topics

### Multiple Sensors in Algorithm

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Use multiple sensors for decision"""
    
    # Read multiple tanks
    t1 = plc_dict.get(('T1', 1), 0.0)
    t2 = plc_cache.get('T2', 0.0)
    t3 = plc_cache.get('T3', 0.0)
    
    # Average level
    avg_level = (t1 + t2 + t3) / 3.0
    
    if avg_level < 3.0:
        return "open"
    else:
        return "closed"
```

**Configuration:**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: multi_tank_algo.py
      dependents: [T1, T2, T3]  # All sensors needed
```

### Using Machine Learning

```python
import pickle
import numpy as np

# Load model once (outside AlgoRun for efficiency)
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """ML-based control"""
    
    # Extract features
    features = [
        plc_dict.get(('T1', 1), 0.0),
        plc_dict.get(('T2', 1), 0.0),
        plc_dict.get(('P1F', 1), 0.0),  # Flow rate
    ]
    
    # Predict
    prediction = model.predict([features])[0]
    
    # Threshold
    if prediction > 0.5:
        return "open"
    else:
        return "closed"
```

### Time-Based Logic

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Schedule-based control"""
    
    from datetime import datetime
    
    current_hour = datetime.now().hour
    
    # Peak hours: 6am-10am, 5pm-10pm
    if (6 <= current_hour <= 10) or (17 <= current_hour <= 22):
        # High demand period - keep pump on
        return "open"
    else:
        # Low demand - use tank level
        tank_level = plc_dict.get(('T1', 1), 0.0)
        if tank_level < 3.0:
            return "open"
        else:
            return "closed"
```

**Configuration:**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: schedule_algo.py
      dependents: [T1]  # Only T1 needed
```

### Stateful Algorithms (Using Global Variables)

```python
# Global state (persists across calls)
pump_on_duration = 0
pump_off_duration = 0

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Prevent rapid cycling"""
    global pump_on_duration, pump_off_duration
    
    MIN_ON_TIME = 10   # iterations
    MIN_OFF_TIME = 10  # iterations
    
    tank_level = plc_dict.get(('T1', 1), 0.0)
    pump_state = plc_dict.get(('P1', 1), 0)
    
    # Track durations
    if pump_state == 1:
        pump_on_duration += 1
        pump_off_duration = 0
    else:
        pump_off_duration += 1
        pump_on_duration = 0
    
    # Control with minimum duration constraints
    if tank_level < 2.0 and pump_off_duration >= MIN_OFF_TIME:
        return "open"
    elif tank_level > 4.0 and pump_on_duration >= MIN_ON_TIME:
        return "closed"
    else:
        # Maintain current state
        return "open" if pump_state == 1 else "closed"
```

### Skip Flag Usage

When you have multiple controls for the same actuator and want to handle them all in one algorithm:

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Handle both ABOVE and BELOW conditions in one call"""
    
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    if tank_level < 2.0:
        # Turn on AND skip further processing
        return ("open", True)
    elif tank_level > 4.0:
        # Turn off AND skip further processing
        return ("closed", True)
    else:
        # Maintain state, no skip needed
        return "rule"
```

The `True` skip flag prevents other controls for this actuator from being evaluated in this iteration.

### Hybrid Mode Algorithm

In `hybridcontrol` mode, algorithms get SCADA commands too:

```python
def AlgoRun(plc_cache, plc_dict, scada_cache):
    """Use both local and SCADA data"""
    
    # Local decision
    tank_level = plc_dict.get(('T1', 1), 0.0)
    local_decision = "open" if tank_level < 3.0 else "closed"
    
    # SCADA command
    scada_command = scada_cache.get('ScadaCommand_P1', None)
    
    # Mirror sensor from SCADA
    scada_tank = scada_cache.get('T1S', None)
    
    # Trust local sensor more than SCADA (detect attack)
    if scada_tank and abs(tank_level - scada_tank) > 0.5:
        # Possible attack - ignore SCADA
        return local_decision
    else:
        # Normal - follow SCADA
        return "scada"
```

### Logging and Debugging

```python
import logging

# Set up logger
logger = logging.getLogger(__name__)

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Algorithm with logging"""
    
    tank_level = plc_dict.get(('T1', 1), 0.0)
    pump_state = plc_dict.get(('P1', 1), 0)
    
    logger.info(f"Tank: {tank_level:.2f}, Pump: {pump_state}")
    
    if tank_level < 2.0:
        logger.info("Turning pump ON - tank low")
        return "open"
    elif tank_level > 4.0:
        logger.info("Turning pump OFF - tank high")
        return "closed"
    else:
        logger.debug("Maintaining current state")
        return "open" if pump_state == 1 else "closed"
```

### Writing to External Files

```python
import csv
from pathlib import Path

# Initialize output file (do once)
output_file = Path('algorithm_decisions.csv')
if not output_file.exists():
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['iteration', 'tank_level', 'decision'])

iteration_counter = 0

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """Log decisions to file"""
    global iteration_counter
    iteration_counter += 1
    
    tank_level = plc_dict.get(('T1', 1), 0.0)
    decision = "open" if tank_level < 3.0 else "closed"
    
    # Write to file
    with open('algorithm_decisions.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([iteration_counter, tank_level, decision])
    
    return decision
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Wrong key 'dependents'" Error

**Error:**
```
Wrong key 'dependents' in {'name': 'P1', 'decision_maker': '...', 'dependents': ['T1']}
```

**Cause:** Old version of WaCSim without the new feature.

**Solution:**
```bash
cd ~/WaCSim
git pull origin Exp
sudo pip3 install -e .
```

#### Issue 2: Sensor Always Returns 0

**Symptoms:** `plc_dict.get(('T1', 1), 0.0)` always returns 0.0

**Possible Causes:**
1. Sensor not in `dependents` list
2. Sensor name typo
3. Sensor not in INP file

**Solution:**
```yaml
# Make sure sensor is in dependents
dependents: [T1]  # Correct sensor name

# Check sensor exists in plcs.yaml
sensors:
  - T1  # Must be listed here
```

#### Issue 3: Algorithm Not Executing

**Symptoms:** Default behavior, algorithm seems ignored

**Possible Causes:**
1. File path wrong
2. `AlgoRun` function not defined
3. Syntax error in algorithm

**Solution:**
```bash
# Check file exists
ls -la path/to/algo.py

# Test algorithm manually
python3 path/to/algo.py

# Check logs
grep "custom algo" output/PLC1_values.csv
```

#### Issue 4: "Module Not Found" Error

**Error:**
```
ModuleNotFoundError: No module named 'sklearn'
```

**Cause:** Algorithm uses packages not installed.

**Solution:**
```bash
# Install required packages
pip3 install scikit-learn pandas numpy

# Or create requirements.txt
pip3 install -r requirements.txt
```

#### Issue 5: Control Not Being Applied

**Symptoms:** Algorithm returns "open" but actuator stays closed

**Possible Causes:**
1. Actuator has INP control that overrides
2. Attack interfering with command
3. SCADA command overriding (in hybrid mode)

**Solution:**
```python
# Add logging to see what's happening
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    result = "open"
    print(f"Returning: {result}")
    print(f"Current state: {plc_dict.get(('P1', 1), 0)}")
    return result
```

#### Issue 6: Can't Access Sensor from Another PLC

**Symptoms:** `plc_cache.get('T2', 0.0)` returns 0.0 but T2 exists

**Cause:** Sensor on different PLC, not in dependents, or network delay

**Solution:**
```yaml
# Add to dependents even if on another PLC
dependents: [T2]

# Or check plc_cache keys
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    print(f"Available in cache: {list(plc_cache.keys())}")
    # ...
```

### Debugging Tips

1. **Print Debugging:**
   ```python
   def AlgoRun(plc_cache, plc_dict, scada_cache=None):
       print(f"plc_dict keys: {list(plc_dict.keys())}")
       print(f"plc_cache keys: {list(plc_cache.keys())}")
       # Your logic...
   ```

2. **Use Log Level Debug:**
   ```yaml
   log_level: debug  # In config.yaml
   ```

3. **Check Output CSVs:**
   ```python
   import pandas as pd
   df = pd.read_csv('output/PLC1_values.csv')
   print(df.head())
   ```

4. **Test Algorithm Standalone:**
   ```python
   # test_algo.py
   from my_algo import AlgoRun
   
   # Mock data
   plc_dict = {('T1', 1): 2.5, ('P1', 1): 0}
   plc_cache = {}
   
   result = AlgoRun(plc_cache, plc_dict)
   print(f"Result: {result}")
   ```

### Getting Help

1. **Check Documentation:** `doc/CustomAlgorithm.rst`
2. **Review Examples:** `examples/` directory
3. **Enable Debug Logging:** `log_level: debug`
4. **Check GitHub Issues:** Look for similar problems
5. **Test Incrementally:** Start simple, add complexity gradually

---

## Summary

### Quick Reference

**Approach 1 (No INP Controls):**
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: algo.py
      dependents: [T1]  # Optional
```

**Approach 2 (With INP Controls):**
```
[CONTROLS]  # In INP file
LINK P1 OPEN IF NODE T1 BELOW 2.0
```
```yaml
- name: PLC1
  actuators:
    - name: P1
      decision_maker: algo.py
      # dependents optional (auto-detected from INP)
```

**Algorithm Template:**
```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    sensor_value = plc_dict.get(('SENSOR', 1), 0.0)
    
    if condition:
        return "open"
    else:
        return "closed"
```

### Best Practices

1. ✅ **Use Approach 1** for new projects (cleaner)
2. ✅ **Specify dependents** explicitly for clarity
3. ✅ **Test algorithms** standalone before integration
4. ✅ **Add logging** for debugging
5. ✅ **Handle edge cases** (sensor missing, NaN values)
6. ✅ **Document your logic** with comments
7. ✅ **Start simple** then add complexity

### Next Steps

1. Try the EdenTown example
2. Modify the odd/even logic
3. Implement your own control strategy
4. Experiment with multiple sensors
5. Try machine learning integration

**Happy Coding!** 🚀

