"""
V4 Valve Control Algorithm
Controls valve V4 based on Tank T2 level and Junction J4 pressure.
Uses failsafe counter to prevent rapid valve cycling.
"""

# Failsafe counter to prevent rapid on/off cycling
failsafe_counter = 0


def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Main algorithm entry point.
    
    Logic:
    - If T2 >= 10: Tank is almost full
        - If J4 <= 57: Pump is off, safe to open valve
        - Else: Close valve (with failsafe delay)
    - Else: Tank not full, open valve to fill
    
    Args:
        plc_cache: Cache dictionary with iteration info
        plc_dict: Dictionary with local sensor values
        scada_cache: Optional SCADA cache
        control: Optional control info
    
    Returns:
        str or tuple: 'rule', ('open', True), or ('closed', True)
    """
    global failsafe_counter
    
    # Extract sensor values
    t2_value = None
    j4_value = None
    
    for (sensor, _), value in plc_dict.items():
        if sensor == 'T2':
            t2_value = value
        elif sensor == 'J4':
            j4_value = value
    
    print(f"[V4_Algo] T2={t2_value}, J4={j4_value}, failsafe={failsafe_counter}")
    
    # Decrement failsafe counter each iteration
    if failsafe_counter > 0:
        failsafe_counter -= 1
    
    # Check tank level
    if t2_value is not None and t2_value >= 10.0:
        # Tank is almost full
        if j4_value is not None and j4_value <= 57.0:
            # Pump is off (low pressure), safe to open valve
            print("[V4_Algo] Pump off (J4 low), opening valve")
            failsafe_counter = 3  # Reset failsafe
            return 'open', True
        else:
            # Pump is running, check failsafe before closing
            if failsafe_counter > 0:
                print("[V4_Algo] Failsafe active, keeping valve open")
                return 'open', True
            else:
                print("[V4_Algo] Tank full, closing valve")
                return 'closed', True
    else:
        # Tank not full, open valve to fill
        print("[V4_Algo] Tank not full, opening valve")
        return 'open', True

