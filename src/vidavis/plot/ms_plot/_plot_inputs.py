''' Utilities for inputs to MeasurementSet plots '''

def inputs_changed(plot_inputs, last_plot_inputs):
    ''' Check if inputs changed and need new plot '''
    if plot_inputs and not last_plot_inputs:
        return True

    for key, val in plot_inputs.items():
        if not _values_equal(val, last_plot_inputs[key]):
            return True
    return False

def _values_equal(val1, val2):
    ''' Test if values are set and equal, or not set (cannot compare value with None) '''
    if val1 is not None and val2 is not None: # both set
        return val1 == val2
    if val1 is None and val2 is None: # both None
        return True
    return False # one set and other is None
