#!/usr/bin/env python3
"""
Tank-Level Dependent Pump Speed Control Algorithm for P1
=========================================================

This algorithm demonstrates INTELLIGENT variable speed pump control.
The pump speed is adjusted based on tank level:
- Low tank level → Higher pump speed (fill faster)
- High tank level → Lower pump speed (fill slower / save energy)

Speed Logic (based on T1 tank level):
- Level < 2.0m  → Speed 1.5 (150%) - URGENT: fill fast!
- Level < 4.0m  → Speed 1.2 (120%) - Need to fill
- Level < 6.0m  → Speed 1.0 (100%) - Normal operation
- Level < 8.0m  → Speed 0.5 (50%)  - Slow down, tank filling up
- Level >= 8.0m → Speed 0.0 (OFF)  - Tank full, save energy

This is more realistic than simple on/off control and demonstrates
the benefit of variable speed pumps for energy efficiency.
"""

import json
import os
import stat

STATE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(STATE_DIR, "P1_speed_state.json")

# Ensure directory has full permissions
if os.path.exists(STATE_DIR):
    try:
        os.chmod(STATE_DIR, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    except:
        pass


def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Custom algorithm for tank-level-dependent pump speed control.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values  
                  Format: {('SENSOR_NAME', 1): value, ...}
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
        control: The control object being evaluated (optional)
    
    Returns:
        float: Pump speed value between 0.0 and 2.0
               0.0 = off, 1.0 = normal, 1.5 = 150% speed
    """
    
    # Get tank T1 level from local sensors
    # The tank level is stored with key ('T1', 1)
    tank_level = None
    
    # Try to get tank level from plc_dict (local sensors)
    if ('T1', 1) in plc_dict:
        tank_level = plc_dict[('T1', 1)]
    # Try from plc_cache if not found locally (PLC4 might receive from other PLCs)
    elif plc_cache is not None and 'T1' in plc_cache.columns:
        try:
            tank_level = plc_cache['T1'].iloc[-1]  # Get latest value
        except:
            pass
    
    # Default tank level if not found (assume low to keep pump running)
    if tank_level is None:
        tank_level = 3.0
    
    # Calculate speed based on tank level
    if tank_level < 2.0:
        # URGENT: Tank very low - pump at maximum speed
        speed = 1.5
    elif tank_level < 4.0:
        # Tank low - pump faster than normal
        speed = 1.2
    elif tank_level < 6.0:
        # Tank at normal level - pump at normal speed
        speed = 1.0
    elif tank_level < 8.0:
        # Tank getting full - slow down pump
        speed = 0.5
    else:
        # Tank full - turn off pump
        speed = 0.0
    
    # Save state for debugging/monitoring
    state = {
        'tank_level': tank_level,
        'speed': speed,
        'iteration_count': 0
    }
    
    try:
        # Load previous iteration count
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                prev_state = json.load(f)
                state['iteration_count'] = prev_state.get('iteration_count', 0) + 1
        
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        os.chmod(STATE_FILE, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    except IOError as e:
        print(f"Warning: Could not save state file: {e}")
    
    return speed
