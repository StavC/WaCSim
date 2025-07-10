import os
import random

import pandas as pd


def update_csv_with_cache(DataDict, csv_file='PLC/data.csv'):
    # Ensure the DataDict is not empty
    if not DataDict:
        raise ValueError("DataDict is empty or invalid")

    # Check if the directory exists; if not, create it
    if not os.path.exists(os.path.dirname(csv_file)):
        try:
            os.makedirs(os.path.dirname(csv_file))
        except OSError as exc:  # Guard
            print('Error creating directory:', exc)

    # Convert DataDict to DataFrame
    df = pd.DataFrame([DataDict])

    # If the file exists, append; otherwise, create a new file
    if os.path.isfile(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        df.to_csv(csv_file, mode='w', header=True, index=False)


def get_csv_pointer(csv_file):
    """Reads the CSV file and returns its content as a pandas DataFrame."""
    if not os.path.isfile(csv_file):
        raise FileNotFoundError(f"The file {csv_file} does not exist.")

    return pd.read_csv(csv_file)



def AlgoRun(cacheDict, LocalSensorsValues):
    # Path to the CSV file
    PLCNAME = 'PLC3'
    prefix = 'examples/EdenTown/PLC_Case/PLCAlgos/'
    csv_file = prefix + f'{PLCNAME}/data.csv'
    print(f'{PLCNAME} LocalSensorsValues:', LocalSensorsValues)
    print(f'{PLCNAME} cacheDict:', cacheDict)

    # Build DataDict from sensor values
    DataDict = {sensor: value for (sensor, _), value in LocalSensorsValues.items()}
    DataDict.update(cacheDict)

    # Check for previous iteration match
    if os.path.exists(csv_file):
        csv_content = get_csv_pointer(csv_file)

        if not csv_content.empty:
            last_row = csv_content.iloc[-1].to_dict()
            if all(last_row.get(key) == value for key, value in DataDict.items() if key in last_row):
                print(f"{PLCNAME} The last row's iteration matches the cacheDict. Skipping update.")
                return 'rule'

    # --- Failsafe logic ---
    failsafe_counter = 0
    if os.path.exists(csv_file):
        csv_content = get_csv_pointer(csv_file)
        if 'FailsafeCounter' in csv_content.columns and not csv_content.empty:
            last_counter = csv_content['FailsafeCounter'].iloc[-1]
            failsafe_counter = max(int(last_counter) - 1, 0)

    DataDict['FailsafeCounter'] = failsafe_counter

    # Write current row with updated failsafe counter
    update_csv_with_cache(DataDict, csv_file)

    # Reload CSV after update
    csv_content = get_csv_pointer(csv_file)

    lenJ4 = len(csv_content['J4'])
    latest = csv_content.iloc[-1]

    if latest['T2'] >= 10.0:
        if latest['J4'] <= 57.0 and lenJ4 > 20:
            print('J4 value is less than 57, meaning that the pump is off hence we can open the valve')
            DataDict['FailsafeCounter'] = 3  # Re-trigger failsafe
            update_csv_with_cache(DataDict, csv_file)
            return 'open', True
        else:
            if latest['FailsafeCounter'] > 0:
                print('Failsafe active: Preventing pump closure for remaining iterations.')
                return 'open', True
            else:
                print('Tank is almost full, closing the valve')
                return 'closed', True
    else:
        print('Tank is not full, opening the valve')
        return 'open', True










