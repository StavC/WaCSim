"""
V5 Valve Control Algorithm
Controls valve V5 based on Tank T1 level and Junction J5 pressure.
Uses failsafe counter to prevent rapid valve cycling.
"""

# Failsafe counter to prevent rapid on/off cycling
failsafe_counter = 0


def AlgoRun(plc_cache, plc_dict, scada_cache=None, control=None):
    """
    Main algorithm entry point.
    
    Logic:
    - If T1 >= 10: Tank is almost full
        - If J5 <= 57: Pump is off, safe to open valve
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
    t1_value = None
    j5_value = None
    
    for (sensor, _), value in plc_dict.items():
        if sensor == 'T1':
            t1_value = value
        elif sensor == 'J5':
            j5_value = value
    
    print(f"[V5_Algo] T1={t1_value}, J5={j5_value}, failsafe={failsafe_counter}")
    
    # Decrement failsafe counter each iteration
    if failsafe_counter > 0:
        failsafe_counter -= 1
    
    # Check tank level
    if t1_value is not None and t1_value >= 10.0:
        # Tank is almost full
        if j5_value is not None and j5_value <= 57.0:
            # Pump is off (low pressure), safe to open valve
            print("[V5_Algo] Pump off (J5 low), opening valve")
            failsafe_counter = 3  # Reset failsafe
            return 'open', True
        else:
            # Pump is running, check failsafe before closing
            if failsafe_counter > 0:
                print("[V5_Algo] Failsafe active, keeping valve open")
                return 'open', True
            else:
                print("[V5_Algo] Tank full, closing valve")
                return 'closed', True
    else:
        # Tank not full, open valve to fill
        print("[V5_Algo] Tank not full, opening valve")
        return 'open', True

