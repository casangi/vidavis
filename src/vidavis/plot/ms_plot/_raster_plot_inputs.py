'''
Class to check and hold inputs for raster plot.
'''

from vidavis.plot.ms_plot._check_raster_inputs import check_inputs

class RasterPlotInputs:
    '''
        Class to set inputs for raster plots from MsRaster functions or GUI.
    '''

    def __init__(self):
        self._plot_inputs = {'selection': {}}

    def get_inputs(self):
        ''' Getter for stored plot inputs '''
        return self._plot_inputs

    def get_input(self, name):
        ''' Getter for stored plot input by name '''
        try:
            return self._plot_inputs[name]
        except KeyError:
            return None

    def set_input(self, name, value):
        ''' Set plot input by name and value '''
        self._plot_inputs[name] = value
        if name == 'selection' and 'data_group_name' in value:
            self._plot_inputs['data_group'] = value['data_group_name']

    def set_selection(self, selection):
        ''' Add selection dict to existing selection in plot inputs '''
        self._plot_inputs['selection'] |= selection
        if 'data_group_name' in selection:
            self._plot_inputs['data_group'] = selection['data_group_name']

    def get_selection(self, key):
        ''' Return value for selection key '''
        try:
            return self.get_input('selection')[key]
        except KeyError:
            return None

    def set_inputs(self, plot_inputs):
        ''' Setter for storing plot inputs from MsRaster.plot() '''
        check_inputs(plot_inputs)
        for key, val in plot_inputs.items():
            self._plot_inputs[key] = val

    def remove_input(self, name):
        ''' Remove plot input with name, if it exists '''
        if name == 'selection':
            self._plot_inputs['selection'] = {}
        else:
            try:
                del self._plot_inputs[name]
            except KeyError:
                pass

    def check_inputs(self):
        ''' Check input values are valid, adjust for data dims '''
        check_inputs(self._plot_inputs)

    def is_layout(self):
        ''' Determine if plot is a layout using plot inputs '''
        # Check if subplots is a layout
        subplots = self.get_input('subplots')
        if subplots is None or subplots == (1, 1):
            return False

        # Subplots is a layout, check if multi plot
        if not self.get_input('clear_plots'):
            return True

        # Check if iteration set and iter_range more than one plot
        iter_length = 0
        if self.get_input('iter_axis') is not None:
            iter_range = self.get_input('iter_range')
            if iter_range is None or iter_range[1] == -1:
                iter_range = self.get_input('auto_iter_range')
            iter_length = len(range(iter_range[0], iter_range[1] + 1))
        return iter_length > 1

    #--------------
    # GUI CALLBACKS
    #--------------

    def set_color_inputs(self, color_mode, color_range):
        ''' Set style params from gui '''
        color_mode = color_mode.split()[0]
        color_mode = None if color_mode == 'No' else color_mode
        self.set_input('color_mode', color_mode)
        self.set_input('color_range', color_range)

    def set_axis_inputs(self, x_axis, y_axis, vis_axis):
        ''' Set plot axis inputs from gui '''
        self.set_input('x_axis', x_axis)
        self.set_input('y_axis', y_axis)
        self.set_input('vis_axis', vis_axis)

    def set_aggregation_inputs(self, aggregator, agg_axes):
        ''' Set aggregation inputs from gui '''
        aggregator = None if aggregator== 'None' else aggregator
        self.set_input('aggregator', aggregator)
        self.set_input('agg_axis', agg_axes) # ignored if aggregator not set

    def set_iteration_inputs(self, iter_axis, iter_range, subplot_rows, subplot_columns):
        ''' Set iteration inputs from gui '''
        iter_axis = None if iter_axis == 'None' else iter_axis
        self.set_input('iter_axis', iter_axis)
        self.set_input('iter_range', iter_range)
        self.set_input('subplots', (subplot_rows, subplot_columns))
