#!/usr/bin/env python3
"""
Example Time-Based Custom Algorithm
====================================

This algorithm demonstrates a pump control that doesn't require a dependent sensor.
Instead, it uses time-based logic to cycle the pump on and off.

This is useful when:
- You want to implement a schedule
- Your logic depends on multiple sensors (not just one dependent)
- You want to use the current iteration/time for control

This is specified in the decision_maker YAML as:
    - name: P2
      decision_maker: custom_algos/time_based_pump.py
      # No dependent field needed
"""

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Custom algorithm for time-based pump control.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
    
    Returns:
        str: "open" or "closed" to indicate desired pump state
    """
    
    # You can access any sensor values from plc_dict
    # For example, if you have multiple tanks:
    # tank1_level = plc_dict.get(('T1', 1), 0.0)
    # tank2_level = plc_dict.get(('T2', 1), 0.0)
    
    # Example: Simple time-based control
    # This is just for demonstration - in a real application,
    # you would get the actual iteration/time from the simulation
    
    # For now, let's implement a simple logic based on available data
    # In a real scenario, you might import time, datetime, or track iterations
    
    # Example: Always keep the pump open for this demo
    # In practice, you'd implement your own logic here:
    # - Read multiple sensors
    # - Check current time/iteration
    # - Apply complex decision logic
    # - Use machine learning models
    # - Read from external files/databases
    
    return "open"
    
    # More sophisticated examples:
    # 1. Multi-sensor decision:
    #    if tank1_level < 3.0 and tank2_level > 5.0:
    #        return "open"
    #
    # 2. Machine learning:
    #    import pickle
    #    with open('model.pkl', 'rb') as f:
    #        model = pickle.load(f)
    #    features = [tank1_level, tank2_level, flow_rate]
    #    prediction = model.predict([features])[0]
    #    return "open" if prediction > 0.5 else "closed"
    #
    # 3. External data:
    #    import json
    #    with open('control_schedule.json') as f:
    #        schedule = json.load(f)
    #    # Use schedule to make decision

