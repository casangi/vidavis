''' Apply selection dict to ProcessingSet and MeasurementSetXds '''

from pandas import to_datetime

import xarray as xr

from vidavis.plot.ms_plot._ms_plot_constants import TIME_FORMAT

def select_ps(ps_xdt, logger, query=None, string_exact_match=True, **kwargs):
    '''
        Apply selection query and kwargs to ProcessingSet using exact match or partial match.
        See https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.ProcessingSetXdt.query
        Select Processing Set first (ps summary columns), then each MeasurementSetXds, where applicable.
        Returns selected ProcessingSet DataTree.
        Throws exception if selection fails.
    '''
    # Do PSXdt selection
    logger.debug(f"Applying selection to ProcessingSet: query={query}, {kwargs}")
    ps_selected_xdt = ps_xdt.xr_ps.query(query=query, string_exact_match=string_exact_match, **kwargs)
    if string_exact_match:
        ps_selected_xdt = _select_ps_ms(ps_selected_xdt, kwargs)
    ps_selected_xdt.attrs = ps_xdt.attrs
    return ps_selected_xdt

#pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
def select_ms(ps_xdt, logger, indexers=None, method=None, tolerance=None, drop=False, **indexers_kwargs):
    ''' Apply selection to each MeasurementSetXdt.
        See https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.MeasurementSetXdt.sel
        Return selected ProcessingSet DataTree.
        Throws exception if selection fails.
    '''
    # Sort out selection by dimension and baseline keywords; xr_ms can only select dims
    dim_selection = None
    time_selection = None
    baseline_selection = None
    if indexers_kwargs:
        logger.debug(f"Applying selection to each MeasurementSet: {indexers_kwargs}")
        dim_selection, time_selection, baseline_selection = _sort_selections(ps_xdt, indexers_kwargs)

    # Report (debug) selected numeric values, possibly using 'nearest' or other method
    selected_ps = xr.DataTree() # return value

    for name, ms_xdt in ps_xdt.items():
        success = True
        try:
            ms_xdt = ms_xdt.xr_ms.sel(indexers=indexers, method=method, tolerance=tolerance, drop=drop, **dim_selection)

            if time_selection:
                ms_xdt, success = _select_time(ms_xdt, time_selection, method, tolerance, drop)

            if success and baseline_selection:
                ms_xdt, success = _select_baseline(ms_xdt, baseline_selection)
        except KeyError:
            # Not in this MS
            success = False

        if success:
            selected_ps[name] = ms_xdt

    if len(selected_ps.keys()) == 0:
        raise KeyError("MeasurementSet selection yielded empty ProcessingSet.")

    selected_ps.attrs = ps_xdt.attrs
    return selected_ps
#pylint: enable=too-many-arguments, too-many-positional-arguments, too-many-locals

def _select_ps_ms(ps_xdt, ps_selection):
    ''' Select MeasurementSets in ProcessingSet according to ps selection.
        Raises exception if selection fails.
    '''
    ms_selected_xdt = xr.DataTree() # return value
    ms_selection = {}
    for key, val in ps_selection.items():
        if key in ['field_name', 'scan_name', 'polarization']:
            ms_selection[key] = val

    # Do selection on each ms_xdt
    for name, ms_xdt in ps_xdt.items():
        # Include ms only if all selections succeed
        success = True

        for key, val in ms_selection.items():
            try:
                if key == 'polarization':
                    ms_xdt = ms_xdt.sel(polarization=val)
                elif key in ['scan_name', 'field_name', 'source_name']:
                    ms_xdt, success = _select_time_dim_coordinate(ms_xdt, key, val)
                    if not success:
                        break
            except KeyError:
                # Selection failed
                success = False
                break
        if success:
            ms_selected_xdt[name] = ms_xdt

    if len(ms_selected_xdt.keys()) == 0:
        raise KeyError("Selection yielded no MeasurementSets in ProcessingSet.")

    return ms_selected_xdt

def _select_time_dim_coordinate(ms_xdt, coordinate, selection):
    ''' Select MeasurementSet coordinate with time dimension. Returns selected ms_xdt and success. '''
    success = False
    times = []
    time_xda = ms_xdt.time

    if isinstance(selection, str):
        selection = [selection]

    # Find times for selection
    for coord_sel in selection:
        sel_time_xda = time_xda.sel(time=time_xda[coordinate]==coord_sel)
        if sel_time_xda.size > 0:
            times.extend(sel_time_xda.values.tolist())

    # Select time in ms_xdt
    if len(times) == 0:
        return ms_xdt, success

    success = True
    if len(times) == 1:
        ms_xdt = ms_xdt.sel(time=times[0])
    else:
        ms_xdt = ms_xdt.sel(time=times)
    return ms_xdt, success

def _sort_selections(ps, selection):
    ''' Separate selection into dimension, time, and baseline/antenna selections '''
    dimension_keys = list(ps.xr_ps.get_max_dims().keys()) # includes 'time'
    baseline_keys = ['antenna1', 'antenna2', 'baseline']

    dim_selection = {}
    time_selection = {}
    baseline_selection = {}

    for key, val in selection.items():
        if key == 'time':
            # Convert time strings to float timestamps
            if isinstance(val, float):
                time_selection['time'] = val
            elif isinstance(val, str):
                time_selection['time'] = to_datetime(val).timestamp()
            elif isinstance(val, list):
                times = []
                for time_sel in val:
                    times.append(to_datetime(time_sel).timestamp())
                time_selection['time'] = times
            elif isinstance(val, slice):
                time_selection['time'] = slice(to_datetime(val.start).timestamp(), to_datetime(val.stop).timestamp(), val.step)
            else:
                raise TypeError(f"Time selection {selection} must be string, list, or slice")
        elif key in dimension_keys:
            dim_selection[key] = val
        elif key in baseline_keys:
            baseline_selection[key] = val
    return dim_selection, time_selection, baseline_selection

def _get_values_for_time_selection(ms_xdt, selection, method, tolerance, drop):
    ''' Return list of times in time_list which can be selected from MeasurementSet. '''
    ms_vals = []
    for val in selection['time']:
        try:
            ms_selection = {'time': val}
            ms_xdt.xr_ms.sel(indexers=None, method=method, tolerance=tolerance, drop=drop, **ms_selection)
            # Selection succeeded, include this value
            ms_vals.append(val)
        except KeyError:
            # Selection failed, do not include value
            continue
    return ms_vals

def _select_time(ms_xdt, selection, method, tolerance, drop):
    ''' Select MeasurementSet time dimension.
        Return selected ms_xdt and whether selection succeeded.
    '''
    if isinstance(selection['time'], slice):
        time_method = None
        time_tolerance = None
    else:
        # set method and tolerance for time value and list selection
        time_method = 'nearest' if method is None else method
        time_tolerance = ms_xdt.time.attrs['integration_time']['data'] if tolerance is None else tolerance

    if isinstance(selection['time'], list):
        # Only use times which exist in this ms, since sel() fails if all items in list cannot be selected.
        ms_times = _get_values_for_time_selection(ms_xdt, selection, time_method, time_tolerance, drop)
        if not ms_times:
            return ms_xdt, False
        ms_time_selection = {'time': ms_times}
        ms_xdt = ms_xdt.xr_ms.sel(indexers=None, method=time_method, tolerance=time_tolerance, drop=drop, **ms_time_selection)
    else:
        # Select str or slice
        ms_xdt = ms_xdt.xr_ms.sel(indexers=None, method=time_method, tolerance=time_tolerance, drop=drop, **selection)
        if ms_xdt.time.size == 0:
            return ms_xdt, False
    return ms_xdt, True

def _get_ms_selected_times(ms_xdt):
    ''' Return list of nearest times selected from ms as time strings '''
    time_attrs = ms_xdt.time.attrs
    try:
        return to_datetime(ms_xdt.time, unit=time_attrs['units'][0], origin=time_attrs['format']).strftime(TIME_FORMAT).values
    except AttributeError:
        return [to_datetime(ms_xdt.time, unit=time_attrs['units'][0], origin=time_attrs['format']).strftime(TIME_FORMAT)]

def _select_baseline(ms_xdt, selection):
    ''' Select MeasurementSet baseline/antenna coordinates.
        Return selected ms_xdt and whether selection succeeded.
    '''
    baseline_ids = []
    baseline_xda = ms_xdt.baseline_id

    for key, val in selection.items():
        if isinstance(val, str):
            baseline_ids.extend(_get_baseline_ids(baseline_xda, key, val))
        elif isinstance(val, list):
            for item in val:
                baseline_ids.extend(_get_baseline_ids(baseline_xda, key, item))
        else:
            raise TypeError("Can only select baselines and antennas by str or list")

    success = len(baseline_ids) > 0
    if success:
        baseline_ids = sorted(list(set(baseline_ids)))
        if len(baseline_ids) == 1:
            ms_xdt = ms_xdt.sel(baseline_id=baseline_ids[0])
        else:
            ms_xdt = ms_xdt.sel(baseline_id=baseline_ids)
    return ms_xdt, success

def _get_baseline_ids(baseline_xda, key, val):
    ''' Return list of baseline_ids for baseline or antenna selections. '''
    if not isinstance(val, str):
        raise TypeError("baseline/antenna selection value must be str")

    antenna1 = None
    antenna2 = None
    if key == 'baseline':
        ant1, ant2 = val.split('&')
        antenna1 = ant1.strip()
        antenna2 = ant2.strip()
    elif key == 'antenna1':
        antenna1 = val
    elif key == 'antenna2':
        antenna2 = val

    try:
        sel_baseline_xda = None
        # Select antenna1
        if antenna1 is not None:
            sel_baseline_xda = baseline_xda.sel(baseline_id=baseline_xda.baseline_antenna1_name==antenna1)

        # Select antenna2
        if antenna2 is not None:
            if sel_baseline_xda is None:
                sel_baseline_xda = baseline_xda.sel(baseline_id=baseline_xda.baseline_antenna2_name==antenna2)
            else:
                sel_baseline_xda = sel_baseline_xda.sel(baseline_id=sel_baseline_xda.baseline_antenna2_name==antenna2)

        # Return baseline ids
        if sel_baseline_xda is not None and sel_baseline_xda.size > 0:
            return sel_baseline_xda.values.tolist()
        return []
    except KeyError:
        return []
