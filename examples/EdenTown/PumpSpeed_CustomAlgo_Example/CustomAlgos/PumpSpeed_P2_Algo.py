#!/usr/bin/env python3
"""
Pump Speed Control Algorithm for P2
====================================

This algorithm demonstrates variable speed pump control for P2.
It uses the same logic as P1 but with its own state file.

Behavior:
- Starts at speed 0.0
- Increments by 0.1 every iteration
- When speed reaches 1.6, resets back to 0.0
- Cycles continuously: 0.0 -> 0.1 -> 0.2 -> ... -> 1.5 -> 0.0 -> ...

Speed Values:
- 0.0 = Pump off
- 1.0 = Pump at 100% (normal speed)
- 1.5 = Pump at 150% (50% faster than normal)
- 2.0 = Pump at 200% (maximum)
"""

import json
import os
import stat

STATE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(STATE_DIR, "P2_speed_state.json")
SPEED_INCREMENT = 0.1
MAX_SPEED = 1.5
RESET_THRESHOLD = 1.6

# Ensure directory has full permissions
if os.path.exists(STATE_DIR):
    try:
        os.chmod(STATE_DIR, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    except:
        pass


def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Custom algorithm for variable speed pump control.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
        control: The control object being evaluated (optional)
    
    Returns:
        float: Pump speed value between 0.0 and 2.0
               0.0 = off, 1.0 = normal, 1.5 = 150% speed
    """
    
    # Load current speed from state file
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                current_speed = state.get('speed', 0.0)
        else:
            current_speed = 0.0
    except (json.JSONDecodeError, IOError):
        current_speed = 0.0
    
    # Calculate new speed
    new_speed = round(current_speed + SPEED_INCREMENT, 1)
    
    # Reset to 0 if we've exceeded the threshold
    if new_speed >= RESET_THRESHOLD:
        new_speed = 0.0
    
    # Save new state
    state = {
        'speed': new_speed,
        'iteration_count': state.get('iteration_count', 0) + 1 if 'state' in dir() else 1
    }
    
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        # Set full permissions for the state file
        os.chmod(STATE_FILE, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    except IOError as e:
        print(f"Warning: Could not save state file: {e}")
    
    # Return the speed value (numeric, not "open"/"closed")
    return new_speed

