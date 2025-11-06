#!/usr/bin/env python3
"""
Odd/Even Tank Level Control Algorithm
======================================

This algorithm demonstrates the NEW FEATURE where custom algorithms 
can be used WITHOUT defining controls in the INP file's [CONTROLS] section.

Control Logic:
- Reads tank T1 level (via the 'dependent' field in YAML)
- If tank level (as integer) is EVEN: Turn pump P1 ON
- If tank level (as integer) is ODD: Turn pump P1 OFF

This is a simple demonstration to show that:
1. No INP control is needed for P1
2. The dependent sensor (T1) is automatically registered
3. Custom algorithm executes at every iteration

YAML Configuration:
    - name: PLC4
      actuators:
        - name: P1
          decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P1_Algo.py
          dependent: T1
"""

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Control pump P1 based on whether tank T1 level is odd or even.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
    
    Returns:
        str: "open" if tank level is even, "closed" if odd
    """
    
    # Get tank T1 level - this sensor is automatically available
    # because we specified it as 'dependent' in the YAML config
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
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

