import os
import pandas as pd


def update_csv_with_cache(DataDict, csv_file='PLC/data.csv'):
    if not DataDict:
        raise ValueError("DataDict is empty or invalid")

    if not os.path.exists(os.path.dirname(csv_file)):
        try:
            os.makedirs(os.path.dirname(csv_file))
        except OSError as exc:
            print('Error creating directory:', exc)

    df = pd.DataFrame([DataDict])

    if os.path.isfile(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        df.to_csv(csv_file, mode='w', header=True, index=False)


def get_csv_pointer(csv_file):
    if not os.path.isfile(csv_file):
        raise FileNotFoundError(f"The file {csv_file} does not exist.")
    return pd.read_csv(csv_file)


def CheckForTeardown(csv_content):
    if 'J1' not in csv_content:
        print("Missing 'J1' column for teardown check.")
        return False

    J1_value = csv_content['J1'].iloc[-1:].values
    print(f"@@@@@@@@J1_value in CheckForTeardown: {J1_value[0]}@@@@@@@@@@@@@")
    if 5 < J1_value[0] <= 56.0:
        print("Teardown condition met: Pressure in J1 is in teardown range.")
        return True

    return False


def CheckForFlowDrop(csv_content, drop_log_file='examples/EdenTown/PLC_Case/PLCAlgos/PLC4/last_drop.txt'):
    if 'P1F' not in csv_content or len(csv_content['P1F']) < 20:
        print("Insufficient data for P1F to detect a drop.")
        return False

    P1F_values = csv_content['P1F'][csv_content['P1F'] > 0].iloc[-2:].values
    if len(P1F_values) < 2:
        print("Not enough non-zero P1F values to detect a drop.")
        return False

    drop = P1F_values[0] - P1F_values[1]  # previous - latest
    print(f"P1F_values: {P1F_values}")
    print(f"Calculated drop: {drop}")

    if 15 <= drop <= 150:
        last_drop = None
        if os.path.exists(drop_log_file):
            with open(drop_log_file, 'r') as f:
                try:
                    last_drop = float(f.read().strip())
                except:
                    last_drop = None

        if last_drop is not None and abs(last_drop - drop) < 0.1:
            print("Same drop already handled. Skipping.")
            return False

        with open(drop_log_file, 'w') as f:
            f.write(str(drop))

        print(f"New flow drop detected: {drop}")
        return True

    print("No significant flow drop detected.")
    return False


def AlgoRun(cacheDict, LocalSensorsValues):
    print('LocalSensorsValues from PLC4 P1 Algo:', LocalSensorsValues)
    print('cacheDict from PLC4 P1 Algo:', cacheDict)

    PLCNAME = 'PLC4'
    prefix = 'examples/EdenTown/PLC_Case/PLCAlgos/'
    csv_file = prefix + f'{PLCNAME}/data.csv'
    STATE_FILE = prefix + f'{PLCNAME}/state.txt'
    DROP_LOG_FILE = prefix + f'{PLCNAME}/last_drop.txt'

    DataDict = {sensor: value for (sensor, _), value in LocalSensorsValues.items()}
    DataDict.update(cacheDict)

    # Check for last recorded row
    csv_content = None
    if os.path.exists(csv_file):
        csv_content = get_csv_pointer(csv_file)
        if not csv_content.empty:
            last_row = csv_content.iloc[-1].to_dict()
            if (
                all(last_row.get(k) == v for k, v in cacheDict.items()) and
                all(last_row.get(k) == v for k, v in LocalSensorsValues.items())
            ):
                print("The last row's data matches current values. Skipping CSV update.")
            else:
                update_csv_with_cache(DataDict, csv_file)
    else:
        update_csv_with_cache(DataDict, csv_file)

    # Ensure updated content is loaded
    csv_content = get_csv_pointer(csv_file)

    # Handle state logic
    current_state = 'rule'
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            current_state = f.read().strip()
        print(f"State file detected with state: {current_state}")

    if current_state == 'closed':
        if CheckForTeardown(csv_content):
            with open(STATE_FILE, 'w') as f:
                f.write('rule')
            if os.path.exists(DROP_LOG_FILE):
                os.remove(DROP_LOG_FILE)
            print("Teardown met. State set to 'rule'. Drop log cleared.")
            return 'rule'
        print("Guard still active. Returning 'closed'.")
        return 'closed', True

    if CheckForFlowDrop(csv_content, drop_log_file=DROP_LOG_FILE):
        with open(STATE_FILE, 'w') as f:
            f.write('closed')
        print("Flow drop detected. State set to 'closed'.")
        return 'closed', True

    print("Normal operation. Returning 'rule'.")
    return 'rule'
