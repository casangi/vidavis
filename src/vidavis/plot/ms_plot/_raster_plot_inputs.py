'''
Class to check and hold inputs for raster plot.
'''

from vidavis.plot.ms_plot._check_raster_inputs import check_inputs

class RasterPlotInputs:
    '''
        Class to set inputs for raster plots from MsRaster functions or GUI.
    '''

    def __init__(self):
        self._inputs = {'ps_selection': [], 'ms_selection': []}

    def get_inputs(self):
        ''' Getter for stored plot inputs '''
        return self._inputs

    def get(self, name):
        ''' Getter for stored plot input by name '''
        try:
            return self._inputs[name]
        except KeyError:
            return None

    def set(self, name, value):
        ''' Set plot input by name and value '''
        self._inputs[name] = value
        if 'selection' in name and 'data_group_name' in value:
            self._inputs['data_group'] = value['data_group_name']

    def set_ps_selection(self, string_exact_match, query, selection):
        ''' Add ProcessingSet selection dict to existing selection in plot inputs '''
        self._inputs['ps_selection'].append({'string_exact_match': string_exact_match, 'query': query, 'selection': selection})
        if 'data_group_name' in selection:
            self._inputs['data_group'] = selection['data_group_name']

# pylint: disable=too-many-arguments, too-many-positional-arguments
    def set_ms_selection(self, indexers, method, tolerance, drop, selection):
        ''' Add MeasurementSet selection dict to existing selection in plot inputs '''
        ms_selection = {'method': method, 'tolerance': tolerance, 'drop': drop}
        if indexers:
            ms_selection['selection'] = indexers
        else:
            ms_selection['selection'] = selection
        self._inputs['ms_selection'].append(ms_selection)

        if 'data_group_name' in selection:
            self._inputs['data_group'] = selection['data_group_name']
# pylint: enable=too-many-arguments, too-many-positional-arguments

    def get_ps_selection(self, key=None):
        ''' Return value for ProcessingSet selection key, or None if key does not exist.
            Return entire selection if key is None.
        '''
        ps_selection = self.get('ps_selection')

        if key:
            for selection in ps_selection:
                try:
                    return selection['selection'][key]
                except KeyError:
                    continue
            return None

        ps_selections = {}
        for selection in ps_selection:
            ps_selections |= selection['selection']

        # Add data group and auto spw selection to return all ps selection
        if 'data_group' in self._inputs:
            ps_selections['data_group'] = self._inputs['data_group']
        if 'auto_spw' in self._inputs:
            ps_selections['spw_name'] = self._inputs['auto_spw']
        return ps_selections

    def get_ms_selection(self, key=None):
        ''' Return value for MeasurementSet selection key, or None if key does not exist.
            Return entire selection if key is None.
        '''
        ms_selection = self.get('ms_selection')

        if key:
            for selection in ms_selection:
                try:
                    return selection['selection'][key]
                except KeyError:
                    continue
            return None

        # Add data group and auto dimension selection to return all ms selection
        ms_selections = {}
        for selection in ms_selection:
            ms_selections |= selection['selection']
        if 'data_group' in self._inputs:
            ms_selections['data_group'] = self._inputs['data_group']
        if 'dim_selection' in self._inputs:
            ms_selections |= self._inputs['dim_selection']
        return ms_selections

    def set_inputs(self, plot_inputs):
        ''' Setter for storing plot inputs from MsRaster.plot() '''
        check_inputs(plot_inputs)
        for key, val in plot_inputs.items():
            self._inputs[key] = val

    def remove(self, key):
        ''' Remove plot input with key, if it exists '''
        if key == 'selection':
            self._inputs['ps_selection'] = []
            self._inputs['ms_selection'] = []
        else:
            try:
                del self._inputs[key]
            except KeyError:
                pass

    def check_inputs(self):
        ''' Check input values are valid, adjust for data dims '''
        check_inputs(self._inputs)

    def is_layout(self):
        ''' Determine if plot is a layout using plot inputs '''
        # Check if subplots is a layout
        subplots = self.get('subplots')
        if subplots is None or subplots == (1, 1):
            return False

        # Subplots is a layout, check if multi plot
        if not self.get('clear_plots'):
            return True

        # Check if iteration set and iter_range more than one plot
        iter_length = 0
        if self.get('iter_axis') is not None:
            iter_range = self.get('iter_range')
            if iter_range is None or iter_range[1] == -1:
                iter_range = self.get('auto_iter_range')
            iter_length = len(range(iter_range[0], iter_range[1] + 1))
        return iter_length > 1

    #--------------
    # GUI CALLBACKS
    #--------------

    def set_color_inputs(self, color_mode, color_range):
        ''' Set style params from gui '''
        color_mode = color_mode.split()[0]
        color_mode = None if color_mode == 'No' else color_mode
        self.set('color_mode', color_mode)
        self.set('color_range', color_range)

    def set_axis_inputs(self, x_axis, y_axis, vis_axis):
        ''' Set plot axis inputs from gui '''
        self.set('x_axis', x_axis)
        self.set('y_axis', y_axis)
        self.set('vis_axis', vis_axis)

    def set_aggregation_inputs(self, aggregator, agg_axes):
        ''' Set aggregation inputs from gui '''
        aggregator = None if aggregator== 'None' else aggregator
        self.set('aggregator', aggregator)
        self.set('agg_axis', agg_axes) # ignored if aggregator not set

    def set_iteration_inputs(self, iter_axis, iter_range, subplot_rows, subplot_columns):
        ''' Set iteration inputs from gui '''
        iter_axis = None if iter_axis == 'None' else iter_axis
        self.set('iter_axis', iter_axis)
        self.set('iter_range', iter_range)
        self.set('subplots', (subplot_rows, subplot_columns))
