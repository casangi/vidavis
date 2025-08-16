'''
    Return x, y, and metadata for cursor position or multiple points in selected box.
    Values are formatted into Panel StaticText and put in row/col format (cursor location)
    or single line (box location).
'''

import numpy as np
from pandas import to_datetime
import panel as pn

from vidavis.plot.ms_plot._ms_plot_constants import TIME_FORMAT

def locate_point(xds, position, vis_axis):
    '''
        Get cursor location as values of coordinates and data vars.
            xds (Xarray Dataset): data for plot
            position (dict): {coordinate: value} of x and y axis positions
            vis_axis (str): visibility component of complex value
        Returns:
            list of pn.widgets.StaticText(name, value) with value formatted for its type
    '''
    static_text_list = []
    values, units = _get_point_location(xds, position, vis_axis)

    # Rename baseline coordinate names to not confuse user for selection
    baseline_names = {'baseline': 'baseline_index', 'baseline_name': 'baseline', 'antenna_name': 'antenna_index', 'antenna': 'antenna_name'}
    for name, value in values.items():
        name = baseline_names[name] if name in baseline_names else name
        static_text = _get_location_text(name, value, units)
        static_text_list.append(static_text)
    return static_text_list

def locate_box(xds, bounds, vis_axis):
    '''
        Get location of each point in box bounds as values of coordinate and data vars.
            xds (Xarray Dataset): data for plot
            bounds (dict): {coordinate: (start, end)} of x and y axis ranges
            vis_axis (str): visibility component of complex value
        Returns:
            list of list of pn.widgets.StaticText(name, value), one list per point.
    '''
    points = []
    npoints = 0

    if xds:
        try:
            selection = {}
            for coord, val in bounds.items():
                # Round index values to int for selection
                selection[coord] = slice(_round_index_value(coord, val[0]), _round_index_value(coord, val[1]))
            sel_xds = xds.sel(indexers=None, method=None, tolerance=None, drop=False, **selection)

            x_coord, y_coord = bounds.keys()
            npoints = sel_xds.sizes[x_coord] * sel_xds.sizes[y_coord]
            counter = 0

            for y in sel_xds[y_coord].values:
                for x in sel_xds[x_coord].values:
                    position = {x_coord: x, y_coord: y}
                    points.append(locate_point(sel_xds, position, vis_axis))
                    counter += 1
                    if counter == 100:
                        break
                if counter == 100:
                    break
        except KeyError:
            pass
    return npoints, points

def _get_point_location(xds, position, vis_axis):
    ''' Select plot data xds with point x, y position, and return coord and data_var values describing the location.
            xds (Xarray Dataset): data for plot
            position (dict): {coordinate: value} of x and y axis positions
            vis_axis (str): visibility component of complex value
        Returns:
            values (dict): {name: value} for each location item
            units (dict): {name: unit} for each value which has a unit defined.
    '''
    values = position.copy()
    units = {}

    if xds:
        try:
            # Round index coordinates to int for selection
            for coord, value in position.items():
                position[coord] = _round_index_value(coord, value)

            sel_xds = xds.sel(indexers=None, method='nearest', tolerance=None, drop=False, **position)
            for coord in sel_xds.coords:
                if coord == 'uvw_label' or ('baseline_antenna' in coord and 'baseline_name' in sel_xds.coords):
                    continue
                val, unit = _get_xda_val_unit(sel_xds[coord])
                values[coord] = val
                units[coord] = unit
            for data_var in sel_xds.data_vars:
                if 'TIME_CENTROID' in data_var:
                    continue
                val, unit = _get_xda_val_unit(sel_xds[data_var])
                if data_var == 'UVW':
                    names = ['U', 'V', 'W']
                    for i, name in enumerate(names):
                        values[name] = val[i]
                        units[name] = unit
                else:
                    values[data_var] = val
                    units[data_var] = unit
        except KeyError:
            pass

    # Set complex component name for visibilities
    if 'VISIBILITY' in values:
        values[vis_axis.upper()] = values.pop('VISIBILITY')
    return values, units

def _round_index_value(coord, value):
    ''' Round index coordinates to int for selecction '''
    return round(value) if coord in ['baseline', 'antenna_name', 'polarization'] else value

def _get_xda_val_unit(xda):
    ''' Return value and unit of xda (selected so only one value) '''
    # Value
    value = xda.values
    if isinstance(value, np.ndarray) and value.size == 1:
        value = value.item()

    # Unit
    try:
        unit = xda.attrs['units']
        unit = unit[0] if (isinstance(unit, list) and len(unit) == 1) else unit
        unit = '' if unit == 'unkown' else unit
    except KeyError:
        unit = ''

    return value, unit

def _get_location_text(name, value, units):
    ''' Format value and unit (if any) and return Panel StaticText '''
    if not isinstance(value, str):
        # Format numeric and datetime values
        if name == "FLAG":
            value = "nan" if np.isnan(value) else int(value)
        elif isinstance(value, float):
            if np.isnan(value):
                value = "nan"
            elif value < 1e6:
                value = f"{value:.4f}"
            else:
                value = f"{value:.4e}"
        elif isinstance(value, np.datetime64):
            value = to_datetime(np.datetime_as_string(value)).strftime(TIME_FORMAT)
            units.pop(name) # no unit for datetime string
    unit = units[name] if name in units else ""
    return pn.widgets.StaticText(name=name, value=f"{value} {unit}")
