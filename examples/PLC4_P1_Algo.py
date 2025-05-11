def AlgoRun(ScadaDict, PLCDict):
    print('Entering AlgoRun HERE' *10)
    print(f'Scada Dict={ScadaDict}')
    print(f'PLC Dict= {PLCDict}')
    if ScadaDict['T41'] > PLCDict['T41'] + 1:
        return 'scada'
    else:
        return 'plc'
