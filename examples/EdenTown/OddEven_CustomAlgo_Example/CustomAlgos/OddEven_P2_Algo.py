#!/usr/bin/env python3
"""
Stateful Alternating Pump Control Algorithm - P2
=================================================

This algorithm demonstrates a STATEFUL custom algorithm that uses a JSON file
to track state across iterations (no INP control needed).

Control Logic:
- 5 iterations with pump OPEN
- 5 iterations with pump CLOSED
- Repeat indefinitely

State Tracking:
- Uses P2_state.json to persist iteration count and current state
- JSON format: {"iteration": N, "state": "open"/"closed"}

This demonstrates:
1. No INP control is needed for P2
2. Custom algorithm maintains state across iterations
3. State persists in a JSON file

YAML Configuration:
    - name: PLC1
      actuators:
        - name: P2
          decision_maker: examples/EdenTown/OddEven_CustomAlgo_Example/CustomAlgos/OddEven_P2_Algo.py
          dependents: []  # No sensors needed for time-based control
"""

import json
import os

# State file path - in same directory as this script
STATE_FILE = os.path.join(os.path.dirname(__file__), "P2_state.json")
ITERATIONS_PER_STATE = 5

def AlgoRun(plc_cache, plc_dict, scada_cache=None):
    """
    Control pump P2 by alternating: 5 iterations open, 5 iterations closed.
    
    Args:
        plc_cache: Dictionary of values received from other PLCs
        plc_dict: Dictionary of local sensor/actuator values
        scada_cache: Dictionary of SCADA commands (in hybrid mode)
    
    Returns:
        str: "open" or "closed" based on iteration count
    """
    
    # Load or initialize state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
    else:
        # Initialize: start with pump open for first 5 iterations
        state = {
            "iteration": 1,
            "state": "open"
        }
    
    # Get current state
    current_iteration = state["iteration"]
    current_state = state["state"]
    
    # Determine action for this iteration
    action = current_state
    
    # Increment iteration counter
    new_iteration = current_iteration + 1
    
    # Check if we need to toggle state (every 5 iterations)
    if new_iteration > ITERATIONS_PER_STATE:
        # Toggle state
        new_state = "closed" if current_state == "open" else "open"
        new_iteration = 1  # Reset counter
    else:
        new_state = current_state
    
    # Save updated state
    state["iteration"] = new_iteration
    state["state"] = new_state
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    return action
