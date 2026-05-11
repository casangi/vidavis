'''
MeasurementSet data backend using xradio Processing Set.
'''

from datetime import datetime, UTC
import os

import numpy as np
import pandas as pd
from pandas import to_datetime

try:
    from vidavis.data.measurement_set.processing_set._ps_io import get_processing_set
    _HAVE_XRADIO = True
    from vidavis.plot.ms_plot._ms_plot_constants import TIME_FORMAT
    from vidavis.data.measurement_set.processing_set._ps_select import select_ps, select_ms
    from vidavis.data.measurement_set.processing_set._ps_stats import calculate_ps_stats
    from vidavis.data.measurement_set.processing_set._ps_raster_data import raster_data
    from vidavis.data.measurement_set.processing_set._xds_data import get_group_correlated_data
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

        # Open processing set from zarr. Converts msv2 if ms path is not zarr
        self._ps_xdt, self._zarr_path = get_processing_set(ms, logger)
        logger.info(f"Processing set contains {len(self._ps_xdt)} MSv4 datasets.")
        self._set_data_groups()

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
                print(f"name: {row[0]}")
                print(f"scan_intents: {row[1]}")
                shape = row[2]
                print(f"shape: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
                print(f"execution_block_UID: {row[3]}")
                print(f"polarization: {row[4]}")
                scans = [str(scan) for scan in row[5]]
                print(f"scan_name: {scans}")
                print(f"spw_name: {row[6]}")
                print(f"spw_intents: {row[7]}")
                fields = [str(field) for field in row[8]]
                print(f"field_name: {fields}")
                sources = [str(source) for source in row[9]]
                print(f"source_name: {sources}")
                lines = [str(line) for line in row[10]]
                print(f"line_name: {lines}")
                field_coords = row[11]
                print(f"field_coords: ({field_coords[0]}) {field_coords[1]} {field_coords[2]}")
                print(f"session_reference_UID: {row[12]}")
                print(f"scheduling_block_UID: {row[13]}")
                print(f"project_UID: {row[14]}")
                print(f"frequency range: {row[15]:e} - {row[16]:e}")
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
        ''' Returns dict of data groups in Processing Set data. '''
        data_groups = {}
        for data_group in self._ms_data_groups.values():
            data_groups |= data_group
        return data_groups

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
        ''' Returns maximum length of dimensions in selected ProcessingSet (if selected) '''
        ps_xdt = self._get_ps_xdt()
        return ps_xdt.xr_ps.get_max_dims()

    def get_data_dimensions(self):
        ''' Return names of the data dimensions. '''
        dims = list(self.get_max_dims().keys())
        if 'uvw_label' in dims:
            dims.remove('uvw_label') # not a VISIBILITY/SPECTRUM data dim
        dims = ['baseline' if dim=='baseline_id' else dim for dim in dims]
        return dims

    def get_dimension_values(self, dimension):
        ''' Return sorted list of unique values for input dimension in selected ProcessingSet.
            For 'time', returns datetime strings.
            For spectrum datasets, 'antenna2' returns empty list.
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
                if dimension not in ms_xdt.coords:
                    if 'antenna1' in dimension and 'antenna_name' in ms_xdt.coords:
                        dimension = 'antenna_name' # spectrum dataset
                    else:
                        continue
                try:
                    dim_values.extend([value.item() for value in ms_xdt[dimension].values])
                except TypeError:
                    dim_values.append(ms_xdt[dimension].values.item())

        if not dim_values:
            return dim_values
        return sorted(set(dim_values))

    def get_dimension_attrs(self, dim):
        ''' Return attributes dict for input dimension in ProcessingSet. '''
        ps_xdt = self._get_ps_xdt()
        return ps_xdt.get(0)[dim].attrs

    def get_first_spw(self, data_group='base'):
        ''' Return first spw name in selected ps summary '''
        spw_names = self.get_summary(data_group)['spw_name']
        return spw_names[0]

    def select_ps(self, string_exact_match=True, query=None, **kwargs):
        ''' Apply data group and summary column selection to ProcessingSet. See ProcessingSetXdt query().
            https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.ProcessingSetXdt.query
            Also applies selection to ms_xdt in ps.
            Selections are cumulative until clear_selection() is called.
            Saves selected ProcessingSet internally.
            Throws exception if selection fails.
        '''
        ps_xdt = self._get_ps_xdt()
        self._selected_ps_xdt = select_ps(ps_xdt, string_exact_match=string_exact_match, query=query, **kwargs)

    def select_ms(self, indexers=None, method=None, tolerance=None, drop=False, **indexers_kwargs):
        ''' Apply dimension and data group selection to MeasurementSet. See MeasurementsSetXdt sel().
            https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.MeasurementSetXdt.sel.
            Additional supported selection besides dimensions include "baseline", "antenna1", "antenna2".
            Selections are cumulative until clear_selection() is called.
            Saves selected ProcessingSet internally.
            Throws exception if selection fails.
        '''
        ps_xdt = self._get_ps_xdt()
        self._selected_ps_xdt = select_ms(ps_xdt, indexers, method, tolerance, drop, **indexers_kwargs)

    def clear_selection(self):
        ''' Clear previous selections and use original ps_xdt '''
        self._selected_ps_xdt = None
        self._ps_xdt, _ = get_processing_set(self._zarr_path, self._logger) # to restore all data groups

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
                return get_group_correlated_data(ms_xdt.ds, data_group)
        raise RuntimeError(f"No correlated data for data group {data_group}")

    def get_raster_data(self, plot_inputs):
        ''' Returns xarray Dataset after applying plot inputs and raster plane selection '''
        return raster_data(self._get_ps_xdt(),
            plot_inputs,
            self._logger
        )

    def flag_name_exists(self, flag_name):
        ''' Check if data variable with flag_name exists in any ms_xdt '''
        for _, data_groups in self._ms_data_groups.items():
            for group in data_groups:
                if flag_name == data_groups[group]['flag']:
                    return True
        return False

# pylint: disable=too-many-locals
    def flag_data(self, src_group_name, flag_selection, flag_name, description):
        ''' Flag selection in source data group flags, using flag_name for new data variable and data group '''
        self._logger.debug(f"Flag data in group {src_group_name} selection {flag_selection}")
        flag_group_name = flag_name.lower()
        flag_data_name = "FLAG_" + flag_name.upper()
        flagged_data_group = {'flag': flag_data_name, 'description': description, 'date': datetime.now(UTC).isoformat()}

        for ms_name in self._ps_xdt:
            ms_xdt = self._ps_xdt[ms_name]
            if src_group_name not in ms_xdt.attrs['data_groups']:
                continue

            # Copy source flag data array
            if flag_data_name not in ms_xdt.data_vars:
                # Deep copy source flag xda to flag_name xda
                src_flag_name = ms_xdt.attrs['data_groups'][src_group_name]['flag']
                ms_xdt[flag_data_name] = ms_xdt[src_flag_name].copy(deep=True)

            # Convert selection data types where needed
            ms_flag_selection = self._convert_flag_selection(ms_xdt, flag_selection)
            if None not in ms_flag_selection.values():
                for pol in ms_flag_selection['polarization']:
                    for baseline_id in ms_flag_selection['baseline_id']:
                        ms_selection = {
                            'time': ms_flag_selection['time'],
                            'frequency': ms_flag_selection['frequency'], 
                            'polarization': pol,
                            'baseline_id': baseline_id,
                        }
                        try:
                            ms_xdt[flag_data_name].loc[ms_selection] = 1.0
                        except KeyError:
                            pass # not in this xds

            # Add new data group to ms, and add to data group dict
            ms_xdt = ms_xdt.xr_ms.add_data_group(flag_group_name, flagged_data_group, src_group_name)
            self._ms_data_groups[ms_name][flag_group_name] = ms_xdt.attrs['data_groups'][flag_group_name]

            # Set flags and data group in ms
            ms_xdt.attrs['data_groups'] = self._ms_data_groups[ms_name] # restore unselected data groups
            ms_zarr_store = os.path.join(self._zarr_path, ms_name)
            ms_xdt.to_zarr(store=ms_zarr_store, mode='a', consolidated=True)
            self._logger.debug(f"Saved flags to {ms_zarr_store}")

        # Write root ps metadata to zarr in append mode
        self._ps_xdt.to_zarr(store=self._zarr_path, mode='a', consolidated=True)
        self._logger.debug(f"Saved data group to {self._zarr_path}")
# pylint: enable=too-many-locals

    def _set_data_groups(self):
        ''' Set dict of data groups per ms in Processing Set data. '''
        self._ms_data_groups = {}
        if self._ps_xdt:
            for ms_name in self._ps_xdt:
                self._ms_data_groups[ms_name] = self._ps_xdt[ms_name].attrs['data_groups']

    def _get_ps_xdt(self):
        ''' Returns selected ps_xdt if selection has been done, else original ps_xdt '''
        return self._selected_ps_xdt if self._selected_ps_xdt else self._ps_xdt

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
        ''' Return baseline strings as ant1_name & ant2_name.
            For spectrum datasets, return list of antenna_name. '''
        baselines = []
        for ms_xdt in ps.values():
            if 'antenna_name' in ms_xdt.coords:
                baselines.extend(ms_xdt.antenna_name.values)
            else:
                ant1_names = ms_xdt.baseline_antenna1_name.values
                ant2_names = ms_xdt.baseline_antenna2_name.values
                for ant1, ant2 in zip(ant1_names, ant2_names):
                    baselines.append(f"{ant1} & {ant2}")
        return baselines

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

    def _convert_flag_selection(self, xds, selection):
        ''' Convert numeric data types to match xds, make str coords a list '''
        flag_selection = {}
        for key, val in selection.items():
            if key == 'time':
                flag_selection['time'] = self._convert_time_selection(xds, val)
            elif key == 'frequency':
                flag_selection['frequency'] = self._convert_frequency_selection(xds, val)
            elif key == 'baseline':
                flag_selection['baseline_id'] = self._convert_baseline_selection(xds, val)
            elif key == 'polarization':
                flag_selection['polarization'] = [val] if isinstance(val, str) else val
        return flag_selection

    def _convert_time_selection(self, xds, time_selection):
        ''' Convert time str to float time in xds '''
        if isinstance(time_selection, float):
            return time_selection

        # Make dict of {datetime: float} to try to get exact float equivalent
        time_attrs = xds.time.attrs
        xds_times = {}
        for float_time in xds.time.values:
            dt_time = to_datetime(float_time, unit=time_attrs['units'], origin=time_attrs['format']).to_datetime64()
            xds_times[dt_time] = float_time

        # Single value
        if isinstance(time_selection, np.datetime64):
            try:
                return xds_times[time_selection]
            except KeyError:
                return None # Not in this MS
        # Slice
        try:
            start = xds_times[time_selection.start]
        except KeyError:
            start = None
        try:
            stop = xds_times[time_selection.stop]
        except KeyError:
            stop = None

        if start is None or stop is None:
            start = time_selection.start.astype(float) / 1e9 if start is None else start
            stop = time_selection.stop.astype(float) / 1e9 if stop is None else stop
            sel_time = xds.time.sel(time=slice(start, stop))
            if sel_time.size == 0:
                return None
            start = sel_time.values[0]
            stop = sel_time.values[-1]
        return start if start == stop else slice(start, stop)

    def _convert_frequency_selection(self, xds, freq_selection):
        ''' Given frequency, select nearest frequency in xds '''
        if isinstance(freq_selection, slice):
            start = self._convert_freq_to_hz(freq_selection.start)
            stop = self._convert_freq_to_hz(freq_selection.stop)
            freq_selection = start if start == stop else slice(start, stop)

        try:
            # Single value
            if isinstance(freq_selection, float):
                sel_xda = xds.frequency.sel(frequency=freq_selection, method='nearest', tolerance=xds.frequency.attrs['channel_width']['data'])
                return sel_xda.values.item()

            # Slice
            sel_xda = xds.frequency.sel(frequency=freq_selection)
            if sel_xda.size >= 1:
                return slice(sel_xda.values[0], sel_xda.values[-1])
            return None
        except KeyError:
            # Frequency not in this xds
            return None

    def _convert_freq_to_hz(self, freq):
        ''' Convert time value to float to match xds type '''
        return freq * 1e9 if freq < 1e9 else freq

    def _convert_baseline_selection(self, xds, baseline_selection):
        ''' Convert baseline name str to baseline_id in xds '''
        if isinstance(baseline_selection, str):
            baseline_selection = [baseline_selection]

        # Make dict of {name: id}
        xds_baselines = {}
        for baseline_id in xds.baseline_id.values:
            baseline_name = f"{xds.baseline_antenna1_name.values[baseline_id]} & {xds.baseline_antenna2_name.values[baseline_id]}"
            xds_baselines[baseline_name] = baseline_id

        baseline_ids = []
        for name in baseline_selection:
            try:
                baseline_ids.append(xds_baselines[name])
            except KeyError:
                pass
        return baseline_ids
