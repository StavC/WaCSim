def AlgoRun(cacheDict):
    print('Entering SCADA AlgoRun HERE' *10)

    if cacheDict['T42'] > 4.0:
        return 'closed'
    else:
        return 'open'
