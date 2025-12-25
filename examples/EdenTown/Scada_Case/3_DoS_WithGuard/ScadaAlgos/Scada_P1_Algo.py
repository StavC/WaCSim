"""
Guard Algorithm for P1 Pump Control (v0.5.1)

This algorithm uses the NEW v0.5.1 feature: Custom algorithms without INP control rules.
- No BELOW/ABOVE rules for P1 in the INP file
- Uses 'dependents: [T1]' in YAML to specify required sensors
- WaCSim creates a synthetic TIME control at iteration 0
- Algorithm has FULL control of P1 from the start

The algorithm handles:
1. Normal operation: Sensor-based control (T1 level thresholds)
2. DoS attack: Historical median cycle times
3. Recovery: Automatic return to sensor-based control
"""

import os
import pandas as pd
import numpy as np

# === Constants ===
CSV_DIR = 'examples/EdenTown/Scada_Case/3_DoS_WithGuard/ScadaAlgos/ScadaData'
CSV_FILE = os.path.join(CSV_DIR, 'scada_data.csv')
STATE_FILE = os.path.join(CSV_DIR, 'GuardRoutineState.txt')
NOISE_THRESHOLD = 0.1
WINDOW_SIZE = 5

# Tank level thresholds (same as original INP rules)
T1_LOW_THRESHOLD = 6.0   # Turn pump ON below this
T1_HIGH_THRESHOLD = 7.0  # Turn pump OFF above this

# Bias factors for cycle times during DoS
MEDIAN_ON_BIAS = -3
MEDIAN_OFF_BIAS = 2


# === CSV Functions ===
def update_csv_with_cache(cache_dict: pd.Series, csv_file: str = CSV_FILE):
    """Appends a new data row from a cache dictionary to the CSV file."""
    if not isinstance(cache_dict, pd.Series) or cache_dict.empty:
        raise ValueError("cache_dict must be a non-empty pandas Series")

    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    df = cache_dict.to_frame().T

    if os.path.isfile(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        df.to_csv(csv_file, mode='w', header=True, index=False)


def get_csv_pointer(csv_file: str = CSV_FILE) -> pd.DataFrame:
    """Reads the entire CSV file into a pandas DataFrame."""
    if not os.path.isfile(csv_file):
        raise FileNotFoundError(f"The file {csv_file} does not exist.")
    return pd.read_csv(csv_file)


# === DoS Detection ===
def compute_DoS_mask(df: pd.DataFrame, noise_threshold: float = NOISE_THRESHOLD,
                     window_size: int = WINDOW_SIZE) -> pd.Series:
    """Computes a boolean mask indicating DoS periods in the data."""
    mask = pd.Series([False] * len(df), index=df.index)
    for i in range(window_size, len(df) + 1):
        window = df['T1'].iloc[i - window_size:i]
        if ((window.max() - window.min()) < noise_threshold) or window.isna().all():
            mask.iloc[i - window_size:i] = True
    return mask


# === Helper Functions for State File ===
def read_state_file(state_file: str = STATE_FILE):
    """Reads the current state of the guard routine from its state file."""
    if not os.path.exists(state_file):
        return None
    with open(state_file, 'r') as f:
        content = f.read().strip()
        if content == 'Safe':
            return 'Safe'
        parts = content.split(',')
        if len(parts) == 3:
            return int(parts[0]), parts[1], int(parts[2])
    return None


def write_state_file(remaining: int, state: str, progress: int, state_file: str = STATE_FILE):
    """Writes the guard routine's current state to the state file."""
    with open(state_file, 'w') as f:
        f.write(f"{remaining},{state},{progress}")


def write_safe_state(state_file: str = STATE_FILE):
    """Writes 'Safe' state indicating normal operation."""
    with open(state_file, 'w') as f:
        f.write('Safe')


# === Core Logic ===
def get_median_cycles(df: pd.DataFrame, dos_mask: pd.Series):
    """Calculates biased median ON/OFF cycle durations from clean historical data."""
    if 'P1' not in df.columns:
        raise ValueError("Missing 'P1' column.")

    clean_df = df[~dos_mask]

    if clean_df.empty:
        return 0, 0

    on_durations, off_durations = [], []
    current_duration, current_state = 0, None

    for _, row in clean_df.iterrows():
        if current_state is None:
            current_state = row['P1']
            current_duration = 1
        elif row['P1'] == current_state:
            current_duration += 1
        else:
            if current_state == 1:
                on_durations.append(current_duration)
            else:
                off_durations.append(current_duration)
            current_state, current_duration = row['P1'], 1

    if current_duration > 0:
        if current_state == 1:
            on_durations.append(current_duration)
        else:
            off_durations.append(current_duration)

    # Apply bias to median calculations
    median_on_raw = int(round(np.median(on_durations))) if on_durations else 0
    median_off_raw = int(round(np.median(off_durations))) if off_durations else 0

    # Apply bias and ensure duration is not negative
    biased_median_on = max(0, median_on_raw + MEDIAN_ON_BIAS)
    biased_median_off = max(0, median_off_raw + MEDIAN_OFF_BIAS)

    return biased_median_on, biased_median_off


def count_interrupted_cycle_duration(df: pd.DataFrame) -> int:
    """
    Counts backward from the last row to find the duration of the current,
    uninterrupted state of P1.
    """
    if df.empty:
        return 0

    last_state = df['P1'].iloc[-1]
    duration = 0
    for i in range(len(df) - 1, -1, -1):
        if df['P1'].iloc[i] == last_state:
            duration += 1
        else:
            break
    return duration


def get_last_pump_state(df: pd.DataFrame) -> str:
    """Returns the last known pump state as 'open' or 'closed'."""
    if df.empty or 'P1' not in df.columns:
        return 'open'  # Default to open if no history
    last_state = df['P1'].iloc[-1]
    return 'open' if last_state == 1 else 'closed'


def CheckForDoSAttack(df: pd.DataFrame) -> bool:
    """Checks if the last few data points indicate an ongoing DoS attack."""
    if len(df) < WINDOW_SIZE:
        return False
    last_window = df['T1'].iloc[-WINDOW_SIZE:]
    return ((last_window.max() - last_window.min()) < NOISE_THRESHOLD) or last_window.isna().all()


def CheckForTeardown(df: pd.DataFrame, noise_threshold: float = NOISE_THRESHOLD) -> bool:
    """Checks for a sudden return to normal operation, indicating DoS teardown."""
    if len(df) < 3:
        return False
    t1 = df['T1'].iloc[-3:].values
    return abs(t1[-1] - t1[-2]) > noise_threshold and abs(t1[-1] - t1[-3]) > noise_threshold


def GuardAlgo(df: pd.DataFrame) -> str:
    """
    Guard algorithm executed during a DoS attack.
    Uses biased median cycle times to maintain pump cycling.
    
    Returns: 'open' or 'closed' (no skip mechanism needed with v0.5.1)
    """
    state_data = read_state_file()

    if state_data is None or state_data == 'Safe':
        print("New DoS event detected. Initializing guard state.")
        dos_mask = compute_DoS_mask(df)
        median_on, median_off = get_median_cycles(df, dos_mask)

        last_cycle_duration = count_interrupted_cycle_duration(df)
        last_cycle_state = df['P1'].iloc[-1]

        initial_state_str = 'open' if last_cycle_state == 1 else 'closed'
        target_duration = median_on if initial_state_str == 'open' else median_off
        remaining = max(0, int(round(target_duration - last_cycle_duration)))

        curr_state = initial_state_str
        progress = last_cycle_duration

        print(f"Pump was {curr_state} for {last_cycle_duration} ticks. Biased median target is {target_duration}. "
              f"ADJUSTED: Will run for {remaining} more ticks.")
    else:
        remaining, curr_state, progress = state_data
        dos_mask = compute_DoS_mask(df)
        median_on, median_off = get_median_cycles(df, dos_mask)

    if remaining > 0:
        remaining -= 1
        progress += 1
        print(f"Guard Action: P1 remains {curr_state}. Remaining ticks: {remaining}, Total progress: {progress}")
    else:
        curr_state = 'open' if curr_state == 'closed' else 'closed'
        new_duration = median_on if curr_state == 'open' else median_off
        remaining = new_duration - 1
        progress = 1
        print(f"Guard Action: Switching P1 to {curr_state}. New biased cycle duration: {new_duration}. Progress: {progress}")

    write_state_file(remaining, curr_state, progress)
    return curr_state  # No skip flag - only one control per actuator now


def NormalControl(cache_dict: pd.Series, df: pd.DataFrame) -> str:
    """
    Normal sensor-based pump control when no attack is detected.
    Replicates the original INP rule logic:
      - LINK P1 OPEN IF NODE T1 BELOW 6
      - LINK P1 CLOSED IF NODE T1 ABOVE 7
    
    Returns: 'open', 'closed', or maintains current state in hysteresis zone
    """
    t1_level = cache_dict.get('T1', None)
    
    # If T1 is not available, maintain current state
    if t1_level is None or pd.isna(t1_level):
        print(f"NormalControl: T1 not available, maintaining current state")
        return get_last_pump_state(df)
    
    if t1_level < T1_LOW_THRESHOLD:
        print(f"NormalControl: T1={t1_level:.2f}m < {T1_LOW_THRESHOLD}m → P1 OPEN")
        return 'open'
    elif t1_level > T1_HIGH_THRESHOLD:
        print(f"NormalControl: T1={t1_level:.2f}m > {T1_HIGH_THRESHOLD}m → P1 CLOSED")
        return 'closed'
    else:
        # In hysteresis zone - maintain current state
        current_state = get_last_pump_state(df)
        print(f"NormalControl: T1={t1_level:.2f}m in hysteresis zone [{T1_LOW_THRESHOLD}-{T1_HIGH_THRESHOLD}] → P1 remains {current_state}")
        return current_state


def AlgoRun(cache_dict: pd.Series):
    """
    Main entry point for the algorithm on each SCADA iteration.
    
    With v0.5.1 (no INP rules for P1):
    - Algorithm has FULL control of P1
    - Returns 'open' or 'closed' directly (no 'rule' fallback)
    - No skip mechanism needed (single synthetic control)
    
    Logic:
    1. Save current SCADA data to CSV for history
    2. Check if DoS attack is in progress
    3. If DoS: Use guard algorithm (median cycle times)
    4. If normal: Use sensor-based control (T1 thresholds)
    """
    # Save current data to CSV
    update_csv_with_cache(cache_dict)
    
    try:
        df = get_csv_pointer()
    except FileNotFoundError:
        # First iteration - no history yet
        df = pd.DataFrame()
    
    # Check for teardown (recovery from DoS)
    if os.path.exists(STATE_FILE) and len(df) >= 3 and CheckForTeardown(df):
        print("Teardown detected. Resetting state to Safe.")
        write_safe_state()
    
    # Check for DoS attack
    if CheckForDoSAttack(df):
        # DoS detected - use guard algorithm
        return GuardAlgo(df)
    else:
        # Normal operation - ensure state is Safe
        state_content = read_state_file()
        if state_content not in [None, 'Safe']:
            print("DoS event ended. Resetting state to Safe.")
            write_safe_state()
        
        # Use sensor-based control
        return NormalControl(cache_dict, df)
