# WaCSim Version 0.5.1 Release Notes

**Release Date**: December 2024

This release introduces two major features that significantly enhance the flexibility and realism of water distribution system simulations.

---

## 🚀 New Features

### 1. Custom Algorithms Without INP Control Rules

Previously, to use a custom algorithm for an actuator (pump or valve), you **had to** define a control rule in the INP file's `[CONTROLS]` section. The custom algorithm would then "override" this rule.

**Now you can create custom algorithms WITHOUT any INP control rules!**

#### How It Works

WaCSim automatically creates **synthetic TIME controls** for actuators that have custom algorithms but no corresponding INP control rules. This gets the actuator into the control loop, and your custom algorithm executes at every iteration.

#### Configuration

In your decision maker YAML file, simply specify the custom algorithm and its dependent sensors:

```yaml
- name: PLC4
  actuators:
    - name: P1
      decision_maker: path/to/your_algorithm.py
      dependents: [T1]  # Sensors needed by your algorithm
```

**Key Fields:**
- `decision_maker`: Path to your Python algorithm file
- `dependents`: List of sensors your algorithm needs (optional, defaults to `[]`)

#### Example Algorithm

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Custom control algorithm.
    
    Args:
        plc_cache: DataFrame of values from other PLCs
        plc_dict: Dict of local sensor values {('SENSOR', 1): value}
        scada_cache: SCADA commands (hybrid mode only)
        control: The control object being evaluated
    
    Returns:
        str: "open", "closed", or "rule"
        float: Numeric value 0.0-2.0 for pump speed (NEW!)
        tuple: (result, skip_flag) to skip further evaluation
    """
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    if tank_level < 3.0:
        return "open"
    elif tank_level > 7.0:
        return "closed"
    else:
        return "rule"  # Fall back to INP control (if exists)
```

#### Benefits

1. **Cleaner INP files**: No need to add dummy control rules
2. **More flexibility**: Full algorithmic control without constraints
3. **Backward compatible**: Existing configurations still work
4. **Automatic sensor registration**: Dependent sensors are automatically available to your algorithm

#### Files Modified

| File | Change |
|------|--------|
| `wacsim/parser/input_parser.py` | Added `generate_synthetic_controls_for_custom_algorithms()` and `add_decision_maker_dependents()` |
| `wacsim/parser/config_parser.py` | Added `dependents` field to decision maker schema |
| `wacsim/python2/generic_plc.py` | Fixed handling of TIME controls without dependants |

---

### 2. Variable Pump Speed Control (0.0 - 2.0)

Previously, pumps could only be controlled as **ON (1) or OFF (0)**. Now custom algorithms can return **numeric speed values** that are passed directly to EPANET's pump speed multiplier!

#### Speed Values

| Value | Meaning | EPANET Effect |
|-------|---------|---------------|
| `0.0` | Pump OFF | No flow |
| `0.5` | 50% speed | Reduced flow (head scales by 0.25) |
| `1.0` | 100% speed | Normal rated operation |
| `1.5` | 150% speed | Increased flow (head scales by 2.25) |
| `2.0` | 200% speed | Maximum operation |

#### Pump Affinity Laws

When you change pump speed, EPANET applies the **affinity laws**:

```
Flow ∝ Speed
Head ∝ Speed²
Power ∝ Speed³
```

**Example**: At 50% speed:
- Flow = 50% of rated
- Head = 25% of rated (0.5² = 0.25)
- Power = 12.5% of rated (0.5³ = 0.125)

#### Example Algorithm with Speed Control

```python
def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Intelligent pump speed control based on tank level.
    """
    tank_level = plc_dict.get(('T1', 1), 3.0)
    
    # Adjust speed based on tank level
    if tank_level < 2.0:
        return 1.5  # 150% - urgent fill!
    elif tank_level < 4.0:
        return 1.2  # 120% - fill faster
    elif tank_level < 6.0:
        return 1.0  # 100% - normal
    elif tank_level < 8.0:
        return 0.5  # 50% - slow down
    else:
        return 0.0  # OFF - tank full
```

#### CSV Output

The results CSV now includes a **PUMP_SPEED** column:

| Column | Description |
|--------|-------------|
| `P1_FLOW` | Pump flow rate (CMH) |
| `P1_STATUS` | Pump on/off status (0 or 1) |
| `P1_SPEED` | **NEW!** Pump speed setting (0.0-2.0) |

#### Important: Pump Curve Selection

⚠️ **When using variable speed, your pump curve matters!**

At reduced speeds, the pump head decreases significantly. If the pump cannot overcome system head (elevation differences + friction), flow will be zero.

**Example Problem:**
- System head requirement: 63.5m (tank elevation - reservoir)
- Pump shutoff head: 150m at full speed
- At 50% speed: 150 × 0.5² = 37.5m
- **37.5m < 63.5m → No flow!**

**Solution:** Use a pump with higher shutoff head:
- Pump shutoff head: 300m
- At 50% speed: 300 × 0.5² = 75m
- **75m > 63.5m → Flow achieved!**

#### Files Modified

| File | Change |
|------|--------|
| `wacsim/physical_process.py` | Changed `int()` to `float()` for reading pump values; Added PUMP_SPEED to CSV output |
| `wacsim/python2/entities/control.py` | Updated `applyScadaDecision()` and `applyHybridDecision()` to pass through numeric values |
| `wacsim/python2/generic_scada.py` | Added handling for numeric speed values |

---

## 📁 New Example: PumpSpeed_CustomAlgo_Example

A complete working example demonstrating both new features:

```
examples/EdenTown/PumpSpeed_CustomAlgo_Example/
├── EdenTown_PumpSpeed.inp              # INP with high-head pump curve (300m)
├── EdenTown_PumpSpeed_config.yaml      # Main configuration
├── EdenTown_PumpSpeed_plc.yaml         # PLC configuration
├── EdenTown_PumpSpeed_decision_plc.yaml # Decision maker with dependents
├── README.md                           # Detailed documentation
└── CustomAlgos/
    ├── PumpSpeed_P1_Algo.py            # P1 speed based on T1 level
    └── PumpSpeed_P2_Algo.py            # P2 speed based on T2 level
```

### Running the Example

```bash
wacsim examples/EdenTown/PumpSpeed_CustomAlgo_Example/EdenTown_PumpSpeed_config.yaml
```

### Expected Results

Watch the CSV output to see:
- Pump speed varying based on tank level
- Flow changing proportionally to speed
- Energy-efficient operation (lower speeds when tanks are filling)

---

## 🔧 Technical Details

### Synthetic Control Generation

When WaCSim detects an actuator with a custom algorithm but no INP control:

1. **Checks** if actuator already has controls from INP file
2. **Skips** built-in decision makers (`rule`, `scada`, `open`, `closed`)
3. **Creates** a TIME control at time 0 with action "open"
4. **Registers** dependent sensors to the PLC

```python
# Generated synthetic control
synthetic_control = {
    "type": "time",
    "value": 0,
    "actuator": actuator_name,
    "action": "open"
}
```

### Speed Value Flow

```
Custom Algorithm → returns 0.7
        ↓
control.applyHybridDecision() → passes through numeric value
        ↓
generic_plc.set_tag() → writes 0.7 to database
        ↓
physical_process.update_controls() → reads 0.7 from database
        ↓
EPANET setlinkvalue(SETTING, 0.7) → pump runs at 70% speed
```

---

## 📋 Migration Guide

### Existing Configurations

**No changes required!** All existing configurations continue to work:
- `"open"` and `"closed"` strings still work
- INP control rules still work
- Existing custom algorithms still work

### Adopting New Features

1. **To use custom algorithms without INP controls:**
   - Remove the INP control rule (optional)
   - Add `dependents: [SENSOR_LIST]` to your decision maker YAML

2. **To use pump speed control:**
   - Return a float (0.0-2.0) instead of "open"/"closed"
   - Ensure your pump curve can deliver head at reduced speeds

---

## 🐛 Bug Fixes

- Fixed `KeyError: 'dependant'` when using TIME controls without dependent sensors
- Fixed debug messages to clarify when custom algorithms are executing
- Added proper handling for numeric speed values in SCADA control mode

---

## 📚 Documentation

- Updated `doc/CustomAlgorithm.rst` with new features
- Created `examples/EdenTown/PumpSpeed_CustomAlgo_Example/README.md`
- Created `examples/EdenTown/OddEven_CustomAlgo_Example/COMPLETE_TUTORIAL.md`

---

## 🙏 Acknowledgments

These features were developed to support more realistic water distribution system simulations, particularly for:
- Variable frequency drive (VFD) pump modeling
- Energy optimization studies
- Advanced control algorithm research

---

**Full Changelog**: Compare with previous version on GitHub

