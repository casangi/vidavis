'''
MeasurementSet data backend using xradio Processing Set.
'''

import numpy as np
import pandas as pd

try:
    from casagui.data.measurement_set.processing_set._ps_io import get_processing_set
    _HAVE_XRADIO = True
    from casagui.plot.ms_plot._ms_plot_constants import TIME_FORMAT
    from casagui.data.measurement_set.processing_set._ps_select import select_ps, select_ms
    from casagui.data.measurement_set.processing_set._ps_stats import calculate_ps_stats
    from casagui.data.measurement_set.processing_set._ps_raster_data import raster_data
    from casagui.data.measurement_set.processing_set._xds_data import get_correlated_data
except ImportError as e:
    _HAVE_XRADIO = False


class PsData:
    '''
    Class implementing data backend using xradio Processing Set for accessing and selecting MeasurementSet data.
    '''

    def __init__(self, ms, logger):
        if not _HAVE_XRADIO:
            raise RuntimeError("xradio package not available for reading MeasurementSet")

        if not ms:
            raise RuntimeError("MS path not available for reading MeasurementSet")

        # Open processing set from zarr
        # Converts msv2 if ms path is not zarr
        self._ps_xdt, self._zarr_path = get_processing_set(ms, logger)

        self._logger = logger
        self._selection = {}
        self._selected_ps_xdt = None # cumulative selection

    def get_path(self):
        ''' Return path to zarr file (input or converted from msv2) '''
        return self._zarr_path

    def summary(self, data_group='base', columns=None):
        ''' Print full or selected summary of Processing Set metadata, optionally by ms '''
        ps_summary = self.get_summary(data_group)
        pd.set_option("display.max_rows", len(self._ps_xdt))
        pd.set_option("display.max_columns", len(ps_summary.columns))
        pd.set_option("display.max_colwidth", None)

        if columns is None:
            print(ps_summary)
        elif columns == "by_ms":
            for row in ps_summary.itertuples(index=False):
                print(f"MSv4 name: {row[0]}")
                print(f"intent: {row[1]}")
                shape = row[2]
                print(f"shape: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
                print(f"polarization: {row[3]}")
                scans = [str(scan) for scan in row[4]]
                print(f"scan_name: {scans}")
                print(f"spw_name: {row[5]}")
                fields = [str(field) for field in row[6]]
                print(f"field_name: {fields}")
                sources = [str(source) for source in row[7]]
                print(f"source_name: {sources}")
                lines = [str(line) for line in row[8]]
                print(f"line_name: {lines}")
                field_coords = row[9]
                print(f"field_coords: ({field_coords[0]}) {field_coords[1]} {field_coords[2]}")
                print(f"frequency range: {row[10]:e} - {row[11]:e}")
                print("-----")
        else:
            if isinstance(columns, str):
                columns = [columns]
            col_df = ps_summary[columns]
            print(col_df)

    def get_summary(self, data_group='base'):
        ''' Return summary of original ps '''
        return self._ps_xdt.xr_ps.summary(data_group)

    def get_data_groups(self):
        ''' Returns set of data group names in Processing Set data. '''
        data_groups = []
        for ms_xdt_name in self._ps_xdt:
            data_groups.extend(list(self._ps_xdt[ms_xdt_name].data_groups))
        return set(data_groups)

    def plot_antennas(self, label_antennas=False):
        ''' Plot antenna positions.
                label_antennas (bool): label positions with antenna names.
        '''
        self._ps_xdt.xr_ps.plot_antenna_positions(label_antennas)

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        ''' Plot the phase center locations of all fields in the Processing Set (original or selected) and label central field.
                label_all_fields (bool); label all fields on the plot
                data_group (str); data group to use for processing.
        '''
        self._ps_xdt.xr_ps.plot_phase_centers(label_all_fields, data_group)

    def get_ps_len(self):
        ''' Returns number of ms_xdt in selected ps_xdt (if selected) '''
        return len(self._get_ps_xdt())

    def get_max_dims(self):
        ''' Returns maximum length of data dimensions in selected ps_xdt (if selected) '''
        ps_xdt = self._get_ps_xdt()
        return ps_xdt.xr_ps.get_max_dims()

    def get_data_dimensions(self):
        ''' Return the maximum dimensions in selected ProcessingSet (if selected) '''
        dims = list(self.get_max_dims().keys())
        if 'uvw_label' in dims:
            dims.remove('uvw_label') # not a VISIBILITY/SPECTRUM data dim
        return dims

    def get_dimension_values(self, dimension):
        ''' Return sorted list of unique values for input dimension in selected ProcessingSet.
            For 'time', returns datetime strings.
        '''
        ps_xdt = self._get_ps_xdt()
        dim_values = []

        if dimension == 'time':
            dim_values = self._get_time_strings(ps_xdt)
        elif dimension == 'baseline':
            dim_values = self._get_baselines(ps_xdt)
        else:
            if dimension == 'antenna1':
                dimension = 'baseline_antenna1_name'
            elif dimension == 'antenna2':
                dimension = 'baseline_antenna2_name'
            for ms_xdt in ps_xdt.values():
                try:
                    dim_values.extend([value.item() for value in ms_xdt[dimension].values])
                except TypeError:
                    dim_values.append(ms_xdt[dimension].values.item())

        return sorted(set(dim_values))

    def _get_time_strings(self, ps):
        ''' Return time values as string not float '''
        times = []
        for ms_xdt in ps.values():
            time_xda = ms_xdt.time
            time_attrs = time_xda.attrs
            date_strings = pd.to_datetime(time_xda, unit=time_attrs['units'][0], origin=time_attrs['format']).strftime(TIME_FORMAT).values
            times.extend(date_strings.tolist())
        return times

    def _get_baselines(self, ps):
        ''' Return baseline strings as ant1_name & ant2_name '''
        baselines = []
        for ms_xdt in ps.values():
            ant1_names = ms_xdt.baseline_antenna1_name.values
            ant2_names = ms_xdt.baseline_antenna2_name.values
            for ant1, ant2 in zip(ant1_names, ant2_names):
                baselines.append(f"{ant1} & {ant2}")
        return baselines

    def get_dimension_attrs(self, dim):
        ''' Return attributes dict for input dimension in ProcessingSet. '''
        ps_xdt = self._get_ps_xdt()
        return ps_xdt.get(0)[dim].attrs

    def get_first_spw(self, data_group='base'):
        ''' Return first spw name in selected ps summary '''
        spw_names = self.get_summary(data_group)['spw_name']
        return spw_names[0]

    def select_ps(self, query=None, string_exact_match=True, **kwargs):
        ''' Apply data group and summary column selection to ProcessingSet. See ProcessingSetXdt query().
            https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.ProcessingSetXdt.query
            Also applies selection to ms_xdt in ps.
            Selections are cumulative until clear_selection() is called.
            Saves selected ProcessingSet internally.
            Throws exception if selection fails.
        '''
        ps_xdt = self._get_ps_xdt()
        self._selected_ps_xdt = select_ps(ps_xdt, self._logger, query=query, string_exact_match=string_exact_match, **kwargs)

    def select_ms(self, indexers=None, method=None, tolerance=None, drop=False, **indexers_kwargs):
        ''' Apply dimension and data group selection to MeasurementSet. See MeasurementsSetXdt sel().
            https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.MeasurementSetXdt.sel.
            Additional supported selection besides dimensions include "baseline", "antenna1", "antenna2".
            Selections are cumulative until clear_selection() is called.
            Saves selected ProcessingSet internally.
            Throws exception if selection fails.
        '''
        ps_xdt = self._get_ps_xdt()
        self._selected_ps_xdt = select_ms(ps_xdt, self._logger, indexers, method, tolerance, drop, **indexers_kwargs)

    def clear_selection(self):
        ''' Clear previous selections and use original ps_xdt '''
        self._selected_ps_xdt = None

    def get_vis_stats(self, ps_selection, vis_axis):
        ''' Returns statistics (min, max, mean, std) for data in data group selected by selection.
                data_group (str): correlated data to use for calculations
                selection (dict): fields and values to select
                vis_axis (str): complex component to apply to data
        '''
        stats_ps_xdt = select_ps(self._ps_xdt, self._logger, query=None, string_exact_match=True, **ps_selection)
        data_group = ps_selection['data_group_name'] if 'data_group_name' in ps_selection else 'base'
        return calculate_ps_stats(stats_ps_xdt, self._zarr_path, vis_axis, data_group, self._logger)

    def get_correlated_data(self, data_group):
        ''' Returns name of 'correlated_data' in Processing Set data_group '''
        ps_xdt = self._get_ps_xdt()
        for ms_xdt in ps_xdt.values():
            if data_group in ms_xdt.attrs['data_groups']:
                return get_correlated_data(ms_xdt.ds, data_group)
        raise RuntimeError(f"No correlated data for data group {data_group}")

    def get_raster_data(self, plot_inputs):
        ''' Returns xarray Dataset after applying plot inputs and raster plane selection '''
        return raster_data(self._get_ps_xdt(),
            plot_inputs,
            self._logger
        )

    def _get_ps_xdt(self):
        ''' Returns selected ps_xdt if selection has been done, else original ps_xdt '''
        return self._selected_ps_xdt if self._selected_ps_xdt else self._ps_xdt

    def _get_unique_values(self, df_col):
        ''' Return unique values in pandas Dataframe column, for summary '''
        values = df_col.to_numpy()
        try:
            # numeric arrays
            return np.unique(np.concatenate(values))
        except ValueError:
            # string arrays
            all_values = [row[0] for row in values]
            return np.unique(np.concatenate(all_values))
