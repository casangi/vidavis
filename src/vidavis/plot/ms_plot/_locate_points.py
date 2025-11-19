'''
    Return x, y, and metadata for cursor position or multiple points in selected box.
    Values are formatted into Panel StaticText and put in row/col format (cursor location)
    or single line (box location).
'''

import numpy as np
from pandas import to_datetime
import panel as pn

from vidavis.plot.ms_plot._ms_plot_constants import TIME_FORMAT

def cursor_changed(cursor, last_cursor):
    ''' Check whether cursor position changed '''
    x, y = cursor
    if not x and not y:
        return False # not cursor callback
    if last_cursor and last_cursor == (x, y):
        return False # same cursor
    return True # new cursor or cursor changed

def points_changed(data, last_points):
    ''' Check whether point positions changed '''
    # No data = {'x': [], 'y': []}
    if not data or (len(data['x']) == 0 and len(data['y']) == 0):
        return False # not points callback
    if last_points and last_points == data:
        return False # same points
    return True # new points, points changed, or points deleted

def box_changed(bounds, last_box):
    ''' Check whether box position changed '''
    # No bounds = None
    if not bounds:
        return False # no data, not box select callback
    if last_box and last_box == bounds:
        return False # same box
    return True # new box, box changed, or box deleted

def update_cursor_location(cursor, plot_axes, xds, cursor_locate_box):
    ''' Show data values for cursor x,y position in cursor location box (pn.WidgetBox) '''
    # Convert plot values to selection values to select plot data
    cursor_locate_box.clear()
    x, y = cursor
    x_axis, y_axis, vis_axis = plot_axes

    cursor_position = {x_axis: x, y_axis: y}
    cursor_location = _locate_point(xds, cursor_position, vis_axis)

    location_column = pn.Column(pn.widgets.StaticText(name="Cursor Location"))
    # Add row of columns to column layout
    location_row = _layout_point_location(cursor_location)
    location_column.append(location_row)
    # Add location column to widget box
    cursor_locate_box.append(location_column)

def update_points_location(data, plot_axes, xds, points_tab_feed):
    ''' Show data values for points in point_draw in tab and log '''
    points_tab_feed.clear()
    locate_log = []
    if data:
        x_axis, y_axis, vis_axis = plot_axes
        message = f"Locate {len(data['x'])} points:"
        locate_log.append(message)
        for point in list(zip(data['x'], data['y'])):
            # Locate point
            point_position = {x_axis: point[0], y_axis: point[1]}
            point_location = _locate_point(xds, point_position, vis_axis)
            # Format location and add to points locate column
            location_layout = _layout_point_location(point_location)
            points_tab_feed.append(location_layout)
            points_tab_feed.append(pn.layout.Divider())

            # Format and add to log
            location_list = [f"{static_text.name}={static_text.value}" for static_text in point_location]
            locate_log.append(", ".join(location_list))
    return locate_log

def update_box_location(bounds, plot_axes, xds, box_tab_feed):
    ''' Show data values for points in box_select in tab and log '''
    box_tab_feed.clear()
    locate_log = []
    if bounds:
        x_axis, y_axis, vis_axis = plot_axes
        box_bounds = {x_axis: (bounds[0], bounds[2]), y_axis: (bounds[1], bounds[3])}
        npoints, point_locations = _locate_box(xds, box_bounds, vis_axis)

        message = f"Locate {npoints} points"
        message += " (only first 100 shown):" if npoints > 100 else ":"
        locate_log.append(message)
        box_tab_feed.append(pn.pane.Str(message))

        for point in point_locations:
            # Format and add to box locate column
            location_layout = _layout_point_location(point)
            box_tab_feed.append(location_layout)
            box_tab_feed.append(pn.layout.Divider())

            # Format and add to log
            location_list = [f"{static_text.name}={static_text.value}" for static_text in point]
            locate_log.append(", ".join(location_list))
    return locate_log

def _locate_point(xds, position, vis_axis):
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

    # List indexed coordinate int value with with str value
    index_coords = {'baseline': 'baseline_name', 'antenna_name': 'antenna', 'polarization': 'polarization_name'}
    for name, value in values.items():
        if name in index_coords.values():
            continue
        if name in index_coords and isinstance(value, int):
            value = f"{values[index_coords[name]]} ({value})" # append name to index
        static_text = _get_location_text(name, value, units)
        static_text_list.append(static_text)
    return static_text_list

def _locate_box(xds, bounds, vis_axis):
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
                selection[coord] = slice(_get_selection_value(coord, val[0]), _get_selection_value(coord, val[1]))
            sel_xds = xds.sel(indexers=None, method=None, tolerance=None, drop=False, **selection)

            x_coord, y_coord = bounds.keys()
            npoints = sel_xds.sizes[x_coord] * sel_xds.sizes[y_coord]
            counter = 0

            for y in sel_xds[y_coord].values:
                for x in sel_xds[x_coord].values:
                    position = {x_coord: x, y_coord: y}
                    points.append(_locate_point(sel_xds, position, vis_axis))
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
            for coord, value in position.items():
                # Round index coordinates to int and convert time to datetime if float for selection
                position[coord] = _get_selection_value(coord, value)

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

def _get_selection_value(coord, value):
    ''' Convert index coordinates to int and float time coordinate to datetime '''
    if coord in ['baseline', 'antenna_name', 'polarization']:
        # Round index coordinates to int for selecction
        value = round(value)
    elif coord == 'time' and isinstance(value, float):
        # Bokeh datetime values are floating-point numbers: milliseconds since the Unix epoch
        value = to_datetime(value, unit='ms', origin='unix')
    return value

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

def _layout_point_location(text_list):
    ''' Layout list of StaticText in row of columns containing 3 rows '''
    location_row = pn.Row()
    location_col = pn.Column()

    for static_text in text_list:
        # 3 entries per column; append to row and start new column
        if len(location_col.objects) == 3:
            location_row.append(location_col)
            location_col = pn.Column()

        static_text.margin = (0, 5) # default (5, 10)
        location_col.append(static_text)

    # Add last column
    location_row.append(location_col)
    return location_row
