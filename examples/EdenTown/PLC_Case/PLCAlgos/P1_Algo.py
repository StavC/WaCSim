
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

def CheckForTeardown(csv_content, noise_threshold=0.1):
    """Checks if the Guard routine should stop based on T41 values."""
    # Get the last three T41 values

    J1_value = csv_content['J1'].iloc[-1:].values

    # Check if the current value differs significantly from both previous values
    print(f"@@@@@@@@J2_value in CheckForTearDown: {J1_value} , {J1_value[0]}@@@@@@@@@@@@@")
    if J1_value[0] <=56.0 and J1_value[0] > 5:
        print("Teardown condition met: Less than 50 Pressure in J1, returning to rule")
        return True

    return False


def CheckForFlowDrop(csv_content):
    lenP1F = len(csv_content['P1F'])
    if 'P1F' not in csv_content or lenP1F < 20:
        print("Insufficient data for P1F to detect a drop.")
        return False

    # Get the last non-zero P1F values
    P1F_values = csv_content['P1F'][csv_content['P1F'] > 0].iloc[-2:].values

    # Check if we have at least two valid values
    if len(P1F_values) < 2:
        print("Not enough non-zero P1F values to detect a drop.")
        return False

    # Calculate the drop
    drop = P1F_values[0] - P1F_values[1]

    print("&&&&&&&&&&&&&&&&&")
    print(f"P1F_values[0]: {P1F_values[0]}, P1F_values[1]: {P1F_values[1]}")
    print(f'drop: {drop}')
    print("&&&&&&&&&&&&&&&&&")

    # Check if the drop is within the specified range (10 to 150)
    if 15 <= drop <= 150:
        print(f"Flow drop detected: {drop}")
        return True
    else:
        print(f"No significant flow drop detected. Drop: {drop}")

    return False







def AlgoRun(cacheDict,LocalSensorsValues):

    # Path to the CSV file
    print('LocalSensorsValues from PLC4 P1 Algo:', LocalSensorsValues)
    #print(f'The type of LocalSensorsValues is {type(LocalSensorsValues)}')
    print('cacheDict from PLC4 P1 Algo:', cacheDict)
    #print(f'The type of cacheDict is {type(cacheDict)}')
    PLCNAME='PLC4'
    prefix = 'examples/EdenTown/PLC_Case/PLCAlgos/'
    csv_file = prefix + f'{PLCNAME}/data.csv'
    STATE_FILE = prefix + f'{PLCNAME}/state.txt'

    DataDict = {sensor: value for (sensor, _), value in LocalSensorsValues.items()}
    DataDict.update(cacheDict)  # Merge cacheDict values into DataDict




    # Read the CSV and get a pointer to its content
    if os.path.exists(csv_file):
        csv_content = get_csv_pointer(csv_file)

        # Check if the last row matches the cacheDict
        if not csv_content.empty:
            last_row = csv_content.iloc[-1].to_dict()
            if (
                    all(last_row.get(key) == value for key, value in cacheDict.items()) and
                    all(last_row.get(key) == value for key, value in LocalSensorsValues.items())
            ):
                print("The last row's iteration matches both cacheDict and LocalSensorsValues. Skipping update.")
                return 'rule'

    # Update the CSV file with the cacheDict


    update_csv_with_cache(DataDict, csv_file)
    # Reload the CSV after the update
    csv_content = get_csv_pointer(csv_file)


    # Check if Guard routine is active

    current_state = 'rule'
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            current_state = f.read().strip()
        print(f"State file detected with state: {current_state}")

    if current_state == 'closed':
        if CheckForTeardown(csv_content):
            with open(STATE_FILE, 'w') as f:
                f.write('rule')
            print("Teardown condition met. State set to 'rule'.")
            return 'rule'
        print("Guard still active. Returning 'closed'.")
        return 'closed', True

    # If no guard active, check for flow drop
    if CheckForFlowDrop(csv_content):
        with open(STATE_FILE, 'w') as f:
            f.write('closed')
        print("Flow drop detected. State set to 'closed'.")
        return 'closed', True

    print("Normal operation. Returning 'rule'.")
    return 'rule'