#!/usr/bin/env python3
"""
Example Custom Algorithm for Pump Control
==========================================

This algorithm demonstrates how to control a pump (P1) based on a tank level (T1)
WITHOUT needing a control rule in the INP file's [CONTROLS] section.

The algorithm implements a simple hysteresis control:
- Turn pump ON when tank level drops below 2.0 meters
- Turn pump OFF when tank level rises above 4.0 meters
- Maintain current state in between

This is specified in the decision_maker YAML as:
    - name: P1
      decision_maker: custom_algos/pump_controller.py
      dependent: T1
"""

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Custom algorithm for pump control based on tank level.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
    
    Returns:
        str: "open", "closed", or "rule" to indicate desired pump state
        tuple: (result, skip) where skip=True prevents re-evaluation
    """
    
    # Get the tank level from local sensors
    # The dependent sensor T1 is automatically registered and available
    tank_level = plc_dict.get(('T1', 1), 0.0)
    
    # Get current pump state to implement hysteresis
    pump_state = plc_dict.get(('P1', 1), 0)  # 0=closed, 1=open
    
    # Hysteresis control logic
    if tank_level < 2.0:
        # Tank is low - turn pump ON to fill it
        return "open"
    elif tank_level > 4.0:
        # Tank is full - turn pump OFF
        return "closed"
    else:
        # Tank level is in the middle range - maintain current state
        if pump_state == 0:
            return "closed"
        else:
            return "open"
    
    # Alternative: You could return "rule" to fall back to INP file controls
    # return "rule"
    
    # Alternative: You can return a tuple to skip further evaluation
    # return ("open", True)  # True means skip any other controls for this actuator

