#!/usr/bin/env python3
"""
Odd/Even Tank Level Control Algorithm for P2
=============================================

This algorithm demonstrates the NEW FEATURE where custom algorithms 
can be used WITHOUT defining controls in the INP file's [CONTROLS] section.

Control Logic:
- Reads tank T2 level (via the 'dependent' field in YAML)
- If tank level (as integer) is EVEN: Turn pump P2 ON
- If tank level (as integer) is ODD: Turn pump P2 OFF

This shows the new feature working with a different pump and tank.

YAML Configuration:
    - name: PLC1
      actuators:
        - name: P2
          decision_maker: examples/EdenTown/PLC_Case/PLCAlgos/OddEven_P2_Algo.py
          dependent: T2
"""

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Control pump P2 based on whether tank T2 level is odd or even.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
    
    Returns:
        str: "open" if tank level is even, "closed" if odd
    """
    
    # Get tank T2 level from network cache (T2 is connected to PLC2, not PLC1)
    # The system automatically makes this available via plc_cache
    tank_level = plc_cache.get('T2', 0.0)
    
    # Convert to integer to check odd/even
    tank_level_int = int(tank_level)
    
    # Determine if odd or even
    is_even = (tank_level_int % 2 == 0)
    
    # Control logic:
    # EVEN tank level -> Pump ON (open)
    # ODD tank level -> Pump OFF (closed)
    if is_even:
        return "open"
    else:
        return "closed"

