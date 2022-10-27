"""
plotms module
"""

import os
import time
from datetime import datetime

import holoviews as hv 
import hvplot.pandas
import numpy as np
import xarray as xr
from bokeh.io import export_svgs
from bokeh.models.formatters import BasicTickFormatter, DatetimeTickFormatter
from bokeh.plotting import figure

from cngi_io import read_ms

try:
    from cairosvg import svg2pdf
    _have_svg2pdf = True
except ImportError:
    _have_svg2pdf = False

_MIN_PLOT_WIDTH = 600
_MIN_PLOT_HEIGHT = 500

def _setup_axis(axis):
    labels = {'uvdist': 'UVdist', 'wtxamp': 'Wt*Amp', 'wtsp': 'WtSp', 'sigmasp': 'SigmaSp'}
    if axis in labels:
        label = labels[axis]
    else:
        label = axis.capitalize()

    if axis == "time":
        date_format = ['%Y-%m-%d %H:%M:%S']
        time_format = ['%H:%M:%S']
        formatter = DatetimeTickFormatter(days=date_format, months=date_format, years=date_format, hours=time_format, minutes=time_format, seconds=time_format)
    else:
        formatter = BasicTickFormatter()

    return (label, formatter)

def _add_axis_unit(axis, first_time):
    units = {"Interval": " (s)", "Frequency": " (GHz)", "Velocity": " (km/s)", "U": " (m)",
             "V": " (m)", "W": " (m)", "Uvdist": " (m)", "Phase": " (deg)"}
    if axis in units:
        return axis + units[axis]
    elif axis == "Time":
        time_string = np.datetime_as_string(first_time)
        date = time_string[0 : time_string.find("T")]
        return axis + " (from " + date + ")"
    else:
        return axis

def _apply_flags(xds):
    flg_xds = xds.copy()
    flags = np.atleast_1d('FLAG')
    for flag_var in flags:
        for data_var in xds.data_vars:
            if flag_var == data_var: continue
            if flg_xds[data_var].dims == flg_xds[flag_var].dims:
                flg_xds[data_var] = flg_xds[data_var].where(flg_xds[flag_var] == 0).astype(xds[data_var].dtype)
    #print("flag xds=", flg_xds)
    return flg_xds

def _get_plot_dataset(xds, xkey, ykey, xaxis, yaxis):
    # Dataset containing plotted axes only
    # Coordinates
    plot_coords = {}
    xdims = list(_get_array_dims(xds, xkey))
    ydims = list(_get_array_dims(xds, ykey))
    # Remove uvw_index since already indexed to get u, v, w
    if 'uvw_index' in xdims: xdims.remove('uvw_index')
    if 'uvw_index' in ydims: ydims.remove('uvw_index')
    for dim in xdims:
        if dim == 'uvw_index': continue
        plot_coords[dim]=xds.coords[dim]
    for dim in ydims:
        if dim == 'uvw_index': continue
        plot_coords[dim]=xds.coords[dim]

    # Data variables
    xvals = _get_data(xds, xkey, xaxis)
    yvals = _get_data(xds, ykey, yaxis)
    plot_data = {}
    plot_data[xaxis] = (xdims, xvals)
    plot_data[yaxis] = (ydims, yvals)

    # Create dataset
    plot_xds = xr.Dataset(
        data_vars=plot_data,
        coords=plot_coords,
    )
    #print("plot xds=", plot_xds)
    return plot_xds

def _get_array_dims(xds, key):
    if isinstance(key, tuple):
        # axis calculated from two values
        dims0 = _get_array_dims(xds, key[0])
        dims1 = _get_array_dims(xds, key[1])
        return dims0 if len(dims0) > len(dims1) else dims1
    if key in xds.data_vars:
        return xds.data_vars[key].dims
    elif key in xds.coords:
        return xds.coords[key].dims
    else:
        raise RuntimeError(f"Column for {key} axis does not exist in MeasurementSet")

def _get_array(xds, key):
    if key in xds.data_vars:
        xda = xds.data_vars[key]
    else:
        xda = xds.coords[key]

    if xda.dtype == np.int32:
        xda = xda.where(xda > np.full((1), np.nan, dtype=np.int32)[0])

    return xda

def _get_values(xda, key, axis):
    if key == 'UVW':
        if axis == "u":
            return xda.sel(uvw_index=0).values
        if axis == "v":
            return xda.sel(uvw_index=1).values
        if axis == "w":
            return xda.sel(uvw_index=2).values
        if axis == "uvdist":
            u = xda.sel(uvw_index=0).values
            v = xda.sel(uvw_index=1).values
            return np.sqrt(u*u + v*v)
    elif key == 'DATA':
        if axis == "amp":
            return np.abs(xda.values)
        if axis == "phase":
            return np.angle(xda.values) * 180.0 / np.pi
        if axis == "real":
            return np.real(xda.values)
        if axis == "imag":
            return np.imag(xda.values)
    elif key == 'chan':
        if axis == 'channel':
            return np.array(range(xda.values.size))
        if axis == 'frequency':
            values = xda.values
            if isinstance(values[0], tuple): # chan is common dimension
                values = np.array([val[0] for val in values])
            return values / 1.0e9 #GHz
    elif key == 'FLAG':
        return xda.values.astype(int)

    return xda.values

def _get_calc_values(xds, key, axis):
    # axis calculated from two values
    if axis == 'wtxamp':
        print("data dims=", xds.data_vars['DATA'].dims)
        weight = _get_data(xds, 'WEIGHT', 'weight')
        amp = _get_data(xds, 'DATA', 'amp')
        print("shape: weight=", weight.shape, "amp=", amp.shape)
        return weight * amp
    else:
        raise RuntimeError(f"axis {axis} not supported")

def _get_data(xds, key, axis):
    if isinstance(key, tuple):
        return _get_calc_values(xds, key, axis)
    else:
        xda = _get_array(xds, key)
        return _get_values(xda, key, axis)

def plotms(vis, xaxis='time', yaxis='amp', title="", plotfile="", showplot=True):
    """Plot visibility axes and show interactive plot or export to file.

    Parameters
    ----------
    vis (str):
        Path to the input visibility file
    xaxis (str):
        Which data to plot as the x-axis, default 'time'
    yaxis (str):
        Which data to plot as the y-axis, default 'amp'
    title (str):
        Title written along top of plot, default yaxis vs. xaxis
    plotfile (str):
        Filename for exported plot
    showplot (bool):
        Whether to show interactive plot in browser tab
    """

    # Check arguments
    if not os.path.exists(vis):
        raise RuntimeError(f"Visibility file {vis} does not exist")

    axis_keys = {# METADATA
                 'scan': 'SCAN_NUMBER',
                 'field': 'FIELD_ID',
                 'time': 'TIME',
                 'interval': 'INTERVAL',
                 'spw': 'spw_id',
                 'channel': 'chan',
                 'frequency': 'chan',
                 #'velocity': 'freq',
                 'corr': 'pol',
                 'antenna1': 'ANTENNA1',
                 'antenna2': 'ANTENNA2',
                 #'baseline': 'baseline',
                 'observation': 'OBSERVATION_ID',
                 'intent': 'STATE_ID',
                 'feed1': 'FEED1',
                 'feed2': 'FEED2',
                 # VISIBILITIES and FLAGS
                 'amp': 'DATA',
                 'phase': 'DATA',
                 'real': 'DATA',
                 'imag': 'DATA',
                 'weight': 'WEIGHT',
                 ##'wtxamp': ('WEIGHT', 'DATA'),
                 'wtsp': 'WEIGHT_SPECTRUM',
                 'sigma': 'SIGMA', 
                 'sigmasp': 'SIGMA_SPECTRUM', 
                 'flag': 'FLAG',
                 # OBSERVATIONAL GEOMETRY
                 'u': 'UVW',
                 'v': 'UVW',
                 'w': 'UVW',
                 'uvdist': 'UVW'
                 #'uwave': 'UVW',
                 #'vwave': 'UVW',
                 #'wwave': 'UVW',
                 #'uvwave': 'UVW',
                 #'azimuth': '',
                 #'elevation': '',
                 #'hourang': '',
                 #'parang': '',
                 # ANTENNA-BASED GEOMETRY
                 #'antenna': '',
                 #'ant-az': '',
                 #'ant-el': '',
                 #'ant-ra': '',
                 #'ant-dec': '',
                 #'ant-parang': '',
                }

    if xaxis not in axis_keys:
        raise RuntimeError("Invalid x-axis option: " + xaxis)
    if yaxis not in axis_keys:
        raise RuntimeError("Invalid y-axis option: " + yaxis)

    xkey = axis_keys[xaxis]
    ykey = axis_keys[yaxis]

    # Read ms into xarray dataset
    print("Reading MeasurementSet")
    ms_xds = read_ms(vis)
    first_time = ms_xds.xds0.data_vars["TIME"].values[0]

    # Set up axis labels and plot title (with simple axis labels)
    xlabel, xformatter = _setup_axis(xaxis)
    ylabel, yformatter = _setup_axis(yaxis)
    if not title:
        msname = os.path.basename(vis)
        title = msname + " " + ylabel + " vs. " +  xlabel
    xlabel = _add_axis_unit(xlabel, first_time)
    ylabel = _add_axis_unit(ylabel, first_time)

    nspw = ms_xds.dims['spw_ids']
    spw_ids = ms_xds.coords['spw_ids'].values

    for spw in range(nspw):
        partition = 'xds' + str(spw)
        if partition not in ms_xds.attrs:
            continue

        print("Plotting spw", spw_ids[spw])
        xds = ms_xds.attrs[partition]
        flg_xds = _apply_flags(xds)
        plot_xds = _get_plot_dataset(flg_xds, xkey, ykey, xaxis, yaxis)

        # Convert to dataframe and plot
        plot_df = plot_xds.to_dataframe()
        plot = plot_df.hvplot.scatter(xaxis, yaxis,
            title=title, xlabel=xlabel, ylabel=ylabel,
            xformatter=xformatter, yformatter=yformatter,
            responsive=True, min_width=_MIN_PLOT_WIDTH, min_height=_MIN_PLOT_HEIGHT,
            rasterize=True, cmap=['blue'], padding=(0.01, 0.01), hover=True)

        if spw == 0:
            layout = plot
        else:
            layout = layout * plot

    if showplot:
        print("Showing plot")
        hvplot.show(layout, title='PlotMS', threaded=True)

    if plotfile != "":
        print("Saving plot to", plotfile)

        if plotfile.endswith(".png"):
            hvplot.save(layout, plotfile)
        elif plotfile.endswith(".svg"):
            bokeh_plot = hv.render(layout)
            # show(bokeh_plot) has points, svg plot does not
            bokeh_plot.output_backend = "svg"
            export_svg(bokeh_plot, filename=plotfile)
        elif plotfile.endswith(".pdf"):
            if _have_svg2pdf:
                fig = hv.render(layout)
                fig.output_backend = "svg"
                export_svgs(fig, filename='tmp.svg')
                svg2pdf(url="tmp.svg", write_to=plotfile)
                os.system("rm tmp.svg")
            else:
                raise RuntimeError("Could not import cairosvg for PDF export")
        else:
            raise ValueError("Invalid output file extension type.  Must be png, svg or pdf")
