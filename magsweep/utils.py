import numpy as np

def parse_entry(entry):
    """
    Parses entry string to extract run information

    Types of input strings...
    sequence: start:end:step
    multiple values: value1, value2, value3
    single value: value1

    Parameters
    ----------
    entry: string to be parsed
    """

    if ":" in entry:
        params = entry.split(":")
        if len(params) == 2:
            start = params[0]
            end = params[1]
            step = 1
            
        elif len(params) == 3:
            start = params[0]
            end = params[1]
            step = params[2]
        else:
            return None
            
        return list(np.arange(int(start), int(end), int(step)))

    elif "," in entry:
        return [int(i) for i in entry.split(",")]

    elif entry == "":
        return None
    
    else:
        return [int(entry)]
        
