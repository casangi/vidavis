'''
    Return x and y values or ranges as dimension labels rather than index values not in original PS.
    Use locate to normalize values first.
'''

import numpy as np

from vidavis.plot.ms_plot._locate_points import index_coords, get_locate_value

def get_flag_value(xds, coord, value):
    ''' Locate single value, then convert index coordinates to names. '''
    value = get_locate_value(xds, coord, value)
    if coord in index_coords and isinstance(value, int):
        return str(xds[index_coords[coord]].values[value])
    return value

def get_flag_range(xds, coord, start, stop):
    ''' Return list of values for index coordinate range, or slice for other coordinates '''
    start = get_locate_value(xds, coord, start)
    if isinstance(start, np.ndarray) and start.size == 1:
        start = start.item()

    stop = get_locate_value(xds, coord, stop)
    if isinstance(stop, np.ndarray) and stop.size == 1:
        stop = stop.item()

    # Return slice
    if coord not in index_coords:
        return slice(start, stop)

    # Return list of str for all index values in range
    flag_range = []
    for val in range(start, stop + 1):
        flag_range.append(get_flag_value(xds, coord, val))
    return flag_range[0] if len(flag_range) == 1 else flag_range
