"""
Guard Algorithm for P1 Pump Control (v0.5.1)

Simple approach:
1. During normal operation: Use sensor-based control (T1 thresholds)
2. When DoS detected: Use historical median cycle times as heuristic
3. Continue current cycle to completion, then alternate at median intervals

No bias, no complexity - just median-based cycling.
"""

import os
import pandas as pd
import numpy as np

# === Paths ===
CSV_DIR = 'examples/EdenTown/Scada_Case/3_DoS_WithGuard/ScadaAlgos/ScadaData'
CSV_FILE = os.path.join(CSV_DIR, 'scada_data.csv')
STATE_FILE = os.path.join(CSV_DIR, 'guard_state.txt')

# === Detection Parameters ===
NOISE_THRESHOLD = 0.1  # T1 variation below this = frozen (DoS)
WINDOW_SIZE = 5        # Number of samples to check for DoS

# === Tank Thresholds (same as original INP rules) ===
T1_LOW = 6.0   # Turn pump ON below this
T1_HIGH = 7.0  # Turn pump OFF above this


# ============== CSV Functions ==============

def save_to_csv(cache_dict: pd.Series):
    """Append current SCADA data to CSV history."""
    os.makedirs(CSV_DIR, exist_ok=True)
    df = cache_dict.to_frame().T
    
    if os.path.isfile(CSV_FILE):
        df.to_csv(CSV_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(CSV_FILE, mode='w', header=True, index=False)


def load_csv() -> pd.DataFrame:
    """Load CSV history. Returns empty DataFrame if file doesn't exist."""
    if os.path.isfile(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame()


# ============== State File ==============

def read_state():
    """
    Read guard state. Returns None if not in guard mode.
    Format: remaining,current_state,median_on,median_off
    """
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, 'r') as f:
            content = f.read().strip()
            if not content or content == 'normal':
                return None
            parts = content.split(',')
            if len(parts) == 4:
                return {
                    'remaining': int(parts[0]),
                    'state': parts[1],  # 'open' or 'closed'
                    'median_on': int(parts[2]),
                    'median_off': int(parts[3])
                }
    except:
        pass
    return None


def write_state(remaining: int, state: str, median_on: int, median_off: int):
    """Save guard state."""
    os.makedirs(CSV_DIR, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        f.write(f"{remaining},{state},{median_on},{median_off}")


def clear_state():
    """Clear guard state (return to normal operation)."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'w') as f:
            f.write('normal')


# ============== Median Calculation ==============

def calculate_medians(df: pd.DataFrame) -> tuple:
    """
    Calculate median ON and OFF durations from historical data.
    Only uses data BEFORE any DoS (clean data).
    
    Returns: (median_on, median_off)
    """
    if df.empty or 'P1' not in df.columns:
        return 5, 5  # Default if no history
    
    # Find where DoS starts (frozen T1 values)
    dos_start = None
    for i in range(WINDOW_SIZE, len(df)):
        window = df['T1'].iloc[i-WINDOW_SIZE:i]
        if (window.max() - window.min()) < NOISE_THRESHOLD:
            dos_start = i - WINDOW_SIZE
            break
    
    # Use only clean data (before DoS)
    clean_df = df.iloc[:dos_start] if dos_start else df
    
    if len(clean_df) < 10:
        return 5, 5  # Not enough data
    
    # Count consecutive ON and OFF durations
    on_durations = []
    off_durations = []
    
    current_state = None
    current_count = 0
    
    for val in clean_df['P1']:
        if current_state is None:
            current_state = val
            current_count = 1
        elif val == current_state:
            current_count += 1
        else:
            # State changed - record duration
            if current_state == 1:
                on_durations.append(current_count)
            else:
                off_durations.append(current_count)
            current_state = val
            current_count = 1
    
    # Don't forget the last run
    if current_count > 0:
        if current_state == 1:
            on_durations.append(current_count)
        else:
            off_durations.append(current_count)
    
    # Calculate medians (use defaults if empty)
    median_on = int(np.median(on_durations)) if on_durations else 5
    median_off = int(np.median(off_durations)) if off_durations else 5
    
    # Ensure at least 1 iteration each
    median_on = max(1, median_on)
    median_off = max(1, median_off)
    
    print(f"Calculated medians from {len(clean_df)} clean samples: ON={median_on}, OFF={median_off}")
    return median_on, median_off


def get_current_cycle_duration(df: pd.DataFrame) -> tuple:
    """
    Count how long the pump has been in its current state.
    Returns: (current_state, duration)
    """
    if df.empty or 'P1' not in df.columns:
        return 1, 0  # Assume ON with 0 duration
    
    current_state = df['P1'].iloc[-1]
    duration = 0
    
    for i in range(len(df) - 1, -1, -1):
        if df['P1'].iloc[i] == current_state:
            duration += 1
        else:
            break
    
    return current_state, duration


# ============== DoS Detection ==============

def is_dos_active(df: pd.DataFrame) -> bool:
    """Check if DoS is currently active (T1 values frozen)."""
    if len(df) < WINDOW_SIZE:
        return False
    
    window = df['T1'].iloc[-WINDOW_SIZE:]
    variation = window.max() - window.min()
    return variation < NOISE_THRESHOLD


def is_dos_ended(df: pd.DataFrame) -> bool:
    """Check if DoS has ended (T1 values varying again)."""
    if len(df) < WINDOW_SIZE:
        return False
    
    window = df['T1'].iloc[-WINDOW_SIZE:]
    variation = window.max() - window.min()
    # Need significant variation to confirm recovery
    return variation > NOISE_THRESHOLD * 2


# ============== Control Logic ==============

def normal_control(t1_level, df: pd.DataFrame) -> str:
    """
    Normal sensor-based control.
    - T1 < 6.0: Turn ON
    - T1 > 7.0: Turn OFF
    - In between: Maintain current state
    """
    if t1_level is None or pd.isna(t1_level):
        # No sensor data - maintain current state
        if df.empty or 'P1' not in df.columns:
            return 'open'
        return 'open' if df['P1'].iloc[-1] == 1 else 'closed'
    
    if t1_level < T1_LOW:
        print(f"NormalControl: T1={t1_level:.2f}m < {T1_LOW}m → OPEN")
        return 'open'
    elif t1_level > T1_HIGH:
        print(f"NormalControl: T1={t1_level:.2f}m > {T1_HIGH}m → CLOSED")
        return 'closed'
    else:
        # Hysteresis zone - maintain current state
        if df.empty or 'P1' not in df.columns:
            return 'open'
        current = 'open' if df['P1'].iloc[-1] == 1 else 'closed'
        print(f"NormalControl: T1={t1_level:.2f}m in [{T1_LOW}-{T1_HIGH}] → maintain {current}")
        return current


def guard_control(df: pd.DataFrame) -> str:
    """
    Guard control during DoS attack.
    Uses median cycle times to maintain pump operation.
    """
    state = read_state()
    
    if state is None:
        # First time entering guard mode
        print("DoS detected! Entering guard mode.")
        
        # Calculate medians from clean historical data
        median_on, median_off = calculate_medians(df)
        
        # Get current pump state and how long it's been running
        current_pump, current_duration = get_current_cycle_duration(df)
        current_state = 'open' if current_pump == 1 else 'closed'
        
        # Calculate how much longer to continue current cycle
        target = median_on if current_state == 'open' else median_off
        remaining = max(0, target - current_duration)
        
        print(f"Pump was {current_state} for {current_duration} iters. "
              f"Target={target}. Will continue for {remaining} more iters.")
        
        write_state(remaining, current_state, median_on, median_off)
        return current_state
    
    else:
        # Already in guard mode - continue cycling
        remaining = state['remaining']
        current_state = state['state']
        median_on = state['median_on']
        median_off = state['median_off']
        
        if remaining > 0:
            # Continue current state
            remaining -= 1
            print(f"Guard: P1 {current_state}, {remaining} iters remaining")
            write_state(remaining, current_state, median_on, median_off)
            return current_state
        else:
            # Time to switch!
            new_state = 'closed' if current_state == 'open' else 'open'
            new_duration = median_on if new_state == 'open' else median_off
            remaining = new_duration - 1  # -1 because this iteration counts
            
            print(f"Guard: Switching P1 to {new_state} for {new_duration} iters")
            write_state(remaining, new_state, median_on, median_off)
            return new_state


# ============== Main Entry Point ==============

def AlgoRun(cache_dict: pd.Series):
    """
    Main algorithm entry point.
    
    1. Save current data to history
    2. Check if DoS is active
    3. If DoS: Use median-based cycling
    4. If normal: Use sensor-based control
    """
    # Save to history
    save_to_csv(cache_dict)
    df = load_csv()
    
    # Get current T1 value
    t1 = cache_dict.get('T1', None)
    
    # Check if in guard mode
    in_guard = read_state() is not None
    
    # Check DoS status
    dos_active = is_dos_active(df)
    
    if dos_active:
        # DoS attack in progress - use guard control
        return guard_control(df)
    else:
        # No DoS detected
        if in_guard:
            # Was in guard mode - check if really recovered
            if is_dos_ended(df):
                print("DoS ended. Returning to normal control.")
                clear_state()
            else:
                # Not sure yet - stay in guard mode
                print("DoS may have ended, but staying in guard mode for safety.")
                return guard_control(df)
        
        # Normal operation
        return normal_control(t1, df)
