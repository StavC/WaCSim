import os
import pandas as pd

def update_csv_with_cache(cacheDict, csv_file='ScadaData/scada_data.csv'):
    # Ensure the cacheDict has values
    if cacheDict.empty:
        raise ValueError("cacheDict is empty or invalid")

    # Check if the directory exists; if not, create it
    if not os.path.exists(os.path.dirname(csv_file)):
        try:
            os.makedirs(os.path.dirname(csv_file))
        except OSError as exc:  # Guard
            print('Error creating directory:', exc)

    #print('cacheDict:', cacheDict)
    #print(f'The type of cacheDict is {type(cacheDict)}')

    # Convert cacheDict (Series) to DataFrame
    df = cacheDict.to_frame().T

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

def CountAvgIterOnP1(csv_content):
    """Calculates the average iterations P1 is on and off."""
    if 'P1' not in csv_content.columns:
        raise ValueError("Required column 'P1' is missing in the CSV content.")

    # Calculate consecutive iterations for P1 being ON and OFF
    on_durations = []
    off_durations = []
    current_duration = 0
    current_state = csv_content['P1'].iloc[0]  # Start with the first state

    for _, row in csv_content.iterrows():
        if row['P1'] == current_state:
            current_duration += 1
        else:
            if current_state == 1:
                on_durations.append(current_duration)
            else:
                off_durations.append(current_duration)
            current_duration = 1
            current_state = row['P1']

    # Capture the last ongoing duration
    if current_duration > 0:
        if current_state == 1:
            on_durations.append(current_duration)
        else:
            off_durations.append(current_duration)

    # Calculate the average durations
    avg_on_iterations = sum(on_durations) / len(on_durations) if on_durations else 0
    avg_off_iterations = sum(off_durations) / len(off_durations) if off_durations else 0

    print(f"Average iterations P1 is ON: {avg_on_iterations:.2f}")
    print(f"Average iterations P1 is OFF: {avg_off_iterations:.2f}")

    return avg_on_iterations, avg_off_iterations

def CheckForDoSAttack(csv_content):
    #Check if T41 value remains around the same value for a long time
    NoiseThreshold=0.1
    Last5ValuesT41=[]
    #check if exists at least 5 values in the csv_content
    if len(csv_content)<5:
        return False
    for i in range(1,6):
        Last5ValuesT41.append(csv_content['T41'].iloc[-i])
    print('Last 5 values of T41:', Last5ValuesT41)
    if ((max(Last5ValuesT41)-min(Last5ValuesT41))<NoiseThreshold):
        print(f'T41 values are within the noise threshold of {NoiseThreshold}')
        return True
    else:
        return False

def CheckForTeardown(csv_content, noise_threshold=0.1):
    """Checks if the Guard routine should stop based on T41 values."""
    if len(csv_content) < 3:
        return False  # Not enough data to compare with two previous values

    # Get the last three T41 values
    t41_values = csv_content['T41'].iloc[-3:].values
    current_value = t41_values[-1]
    previous_value_1 = t41_values[-2]
    previous_value_2 = t41_values[-3]

    # Check if the current value differs significantly from both previous values
    if (abs(current_value - previous_value_1) > noise_threshold and
        abs(current_value - previous_value_2) > noise_threshold):
        print("Teardown condition met: T41 has deviated significantly.")
        return True

    return False


def GuardAlgo(csv_content, state_file='GuardRoutineState.txt'):
    """Executes the Guard routine by controlling P1's state and returns 'open' or 'close'."""
    avg_on_iterations, avg_off_iterations = CountAvgIterOnP1(csv_content)

    # Check or initialize the state file
    if not os.path.exists(state_file):
        with open(state_file, 'w') as f:
            f.write(f"{avg_off_iterations},closed")  # Start with 'close' state

    # Read the state
    with open(state_file, 'r') as f:
        remaining_iterations, current_state = f.readline().strip().split(',')

    remaining_iterations = int(round(float(remaining_iterations)))

    # Perform the Guard routine
    if remaining_iterations > 0:
        remaining_iterations -= 1
        print(f"P1 is currently {current_state}. Remaining iterations: {remaining_iterations}")
    else:
        # Switch state
        current_state = 'open' if current_state == 'closed' else 'closed'
        remaining_iterations = avg_on_iterations if current_state == 'open' else avg_off_iterations
        print(f"Switching P1 to {current_state}. New cycle started.")

    # Update the state file
    with open(state_file, 'w') as f:
        f.write(f"{remaining_iterations},{current_state}")

    return current_state





def AlgoRun(cacheDict):
    # Path to the CSV file
    prefix='examples/MiniAnyTownForPaper/Final/ScadaDoS2/ScadaAlgos/'
    csv_file = prefix+'ScadaData/scada_data.csv'

    # Read the CSV and get a pointer to its content
    if os.path.exists(csv_file):
        csv_content = get_csv_pointer(csv_file)

        # Check if the last row matches the cacheDict
        if not csv_content.empty:
            last_row = csv_content.iloc[-1]
            if last_row['iteration'] == cacheDict['iteration']:
                print("The last row's iteration matches the cacheDict. Skipping update.")
                return 'rule'

    # Update the CSV file with the cacheDict
    update_csv_with_cache(cacheDict, csv_file)

    # Reload the CSV after the update
    csv_content = get_csv_pointer(csv_file)

    state_file = prefix+'GuardRoutineState.txt'

    # Check if Guard routine is active
    if os.path.exists(state_file):
        # Perform teardown check
        if CheckForTeardown(csv_content):
            print("Guard routine stopped due to T41 value change. (seems like the DoS is over)")
            os.remove(state_file)  # Remove the state file to exit the guard routine
            return 'rule'

    # Check for DoS attack and start Guard routine if detected
    if CheckForDoSAttack(csv_content):
        state = GuardAlgo(csv_content)
        print(f"Guard routine action: {state}")
        return state, True

    print("No DoS attack detected.")
    return 'rule'







"""
# Example usage
if __name__ == "__main__":
    # Example cacheDict as a pandas Series
    cacheDict = pd.Series({
        "timestamp": pd.Timestamp.now().isoformat(),
        "P79": 1,
        "ScadaCommand_P79": 0,
        "ScadaCommand_P1": 0,
        "ScadaCommand_V1": 0,
        "ScadaCommand_V2": 0,
        "T41": 3.051,
        "T42": 3.051,
        "P1": 1,
        "J2": 0,
        "J13": 0,
        "V1F": 0,
        "V2F": 0
    })

    # Call AlgoRun with the example cacheDict
    AlgoRun(cacheDict)"""