"""
P1 Pump Control Algorithm with Guard Logic
Detects flow drops (potential attack) and closes pump to protect the system.
"""

import os

# State file paths (relative to execution directory)
STATE_FILE = 'P1_guard_state.txt'
DROP_CACHE_FILE = 'P1_drop_cache.txt'

# Store previous values for flow drop detection
previous_p1f_values = []

# Track if we've initialized this run
_initialized = False


def initialize_run():
    """
    Clean up state files at the start of each simulation run.
    Called once when the algorithm first runs.
    """
    global _initialized, previous_p1f_values
    
    if _initialized:
        return
    
    # Delete state files from previous runs
    for state_file in [STATE_FILE, DROP_CACHE_FILE]:
        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"[P1_Algo] Cleaned up {state_file}")
    
    # Reset in-memory state
    previous_p1f_values = []
    _initialized = True
    print("[P1_Algo] Initialized for new run")


def detect_flow_drop(current_p1f):
    """
    Detect significant flow drops that may indicate an attack.
    Returns True if a new significant drop is detected.
    """
    global previous_p1f_values
    
    # Store current value
    if current_p1f > 0:
        previous_p1f_values.append(current_p1f)
    
    # Need at least 2 values to detect a drop
    if len(previous_p1f_values) < 2:
        return False
    
    # Keep only last 20 values
    if len(previous_p1f_values) > 20:
        previous_p1f_values = previous_p1f_values[-20:]
    
    # Get last two non-zero values
    recent_values = [v for v in previous_p1f_values if v > 0][-2:]
    if len(recent_values) < 2:
        return False
    
    drop = recent_values[0] - recent_values[1]
    fingerprint = f"{recent_values[0]:.2f}_{recent_values[1]:.2f}"
    
    # Read past fingerprints to avoid duplicate detections
    past_fingerprints = set()
    if os.path.exists(DROP_CACHE_FILE):
        with open(DROP_CACHE_FILE, 'r') as f:
            past_fingerprints = set(line.strip() for line in f if line.strip())
    
    # Skip if already handled
    if fingerprint in past_fingerprints:
        return False
    
    # Check for significant drop (25-150 units)
    if 25 <= drop <= 150:
        print(f"[P1_Algo] New flow drop detected: {drop:.2f}")
        with open(DROP_CACHE_FILE, 'a') as f:
            f.write(fingerprint + '\n')
        return True
    
    return False


def check_teardown(j1_pressure):
    """
    Check if guard should deactivate based on J1 pressure.
    Returns True if pressure is low enough to return to normal operation.
    """
    if 5 < j1_pressure <= 58.0:
        print(f"[P1_Algo] Teardown: J1 pressure {j1_pressure:.2f} <= 58, returning to normal")
        return True
    return False


def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Main algorithm entry point.
    
    Args:
        plc_cache: Cache dictionary with iteration info
        plc_dict: Dictionary with local sensor values
        scada_cache: Optional SCADA cache (not used here)
        control: Optional control info
    
    Returns:
        str or tuple: 'rule' for normal operation, ('closed', True) to force close
    """
    # Initialize on first call (cleans up state from previous runs)
    initialize_run()
    
    # Extract sensor values
    j1_value = None
    p1f_value = None
    
    for (sensor, _), value in plc_dict.items():
        if sensor == 'J1':
            j1_value = value
        elif sensor == 'P1F':
            p1f_value = value
    
    print(f"[P1_Algo] J1={j1_value}, P1F={p1f_value}")
    
    # Read current guard state
    current_state = 'rule'
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            current_state = f.read().strip()
    
    # If guard is active (pump closed), check for teardown
    if current_state == 'closed':
        if j1_value is not None and check_teardown(j1_value):
            with open(STATE_FILE, 'w') as f:
                f.write('rule')
            print("[P1_Algo] Teardown triggered - OPENING pump")
            return 'open', True  # Explicitly open pump, don't rely on INP rules
        print("[P1_Algo] Guard active, keeping pump closed")
        return 'closed', True
    
    # Normal operation - check for flow drop (attack indicator)
    if p1f_value is not None and detect_flow_drop(p1f_value):
        with open(STATE_FILE, 'w') as f:
            f.write('closed')
        print("[P1_Algo] Attack detected! Closing pump")
        return 'closed', True
    
    # Normal operation
    return 'rule'

