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



def AlgoRun(cacheDict,LocalSensorsValues):
    # Path to the CSV file
    PLCNAME = 'PLC3'
    prefix = 'examples/MiniAnyTownForPaper/Final/LocalPLCDef/PLCAlgos/'
    csv_file = prefix + f'{PLCNAME}/data.csv'
    print(f'{PLCNAME} LocalSensorsValues:', LocalSensorsValues)
    print(f'{PLCNAME} cacheDict:', cacheDict)

    DataDict = {sensor: value for (sensor, _), value in LocalSensorsValues.items()}
    DataDict.update(cacheDict)  # Merge cacheDict values into DataDict


    # Read the CSV and get a pointer to its content
    if os.path.exists(csv_file):
        csv_content = get_csv_pointer(csv_file)

        # Check if the last row matches the cacheDict
        if not csv_content.empty:
            last_row = csv_content.iloc[-1].to_dict()
            if all(last_row.get(key) == value for key, value in DataDict.items()): #
                print(f"{PLCNAME} The last row's iteration matches the cacheDict. Skipping update.")
                return 'rule'

    # Update the CSV file with the cacheDict 2


    update_csv_with_cache(DataDict, csv_file)

    # Reload the CSV after the update
    csv_content = get_csv_pointer(csv_file)


    lenJ4 = len(csv_content['J4'])
    if csv_content['T2'].iloc[-1:].values[0] >=10.0:
        if csv_content['J4'].iloc[-1:].values[0] <=57.0 and lenJ4 > 20:
            print(f'J4 value is less than 50, meaning that the pump is off hence we can open the valve')
            return 'open',True
        else:

            print('Tank is almost full, closing the valve')
            return 'closed',True

    else:
        print('Tank is not full, opening the valve')
        return 'open', True









