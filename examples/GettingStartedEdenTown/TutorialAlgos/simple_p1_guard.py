"""
Simple custom algorithm for the Evolving Tutorial.
P1 pump: open when junction J1 pressure is below a threshold, else closed.
Shows the AlgoRun(plc_cache, plc_dict) interface for PLC mode.
"""

def AlgoRun(plc_cache, plc_dict):
    # Get J1 pressure; keys may be ('J1', 1) or 'J1'
    j1 = plc_dict.get(('J1', 1)) or plc_dict.get('J1')
    if j1 is None and plc_cache:
        j1 = plc_cache.get('J1') or plc_cache.get(('J1', 1))
    if j1 is None:
        return 'rule'  # fallback to INP rule if no data
    # Simple threshold: pump on when pressure low
    if j1 < 20.0:
        return 'open'
    return 'closed'
