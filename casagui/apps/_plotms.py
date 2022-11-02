"""
plotms module
"""

import os
import time
from datetime import datetime

import holoviews as hv 
import hvplot.pandas
import numpy as np
import panel as pn
import xarray as xr
from bokeh.io import export_svgs
from bokeh.models.formatters import BasicTickFormatter, DatetimeTickFormatter
from bokeh.plotting import figure

from casacore.measures import measures
from casacore.quanta import constants, quantity
from cngi_io import read_ms

try:
    from cairosvg import svg2pdf
    _have_svg2pdf = True
except ImportError:
    _have_svg2pdf = False

_PLOT_WIDTH = 800
_PLOT_HEIGHT = 400

def _get_freq_params(xds, xaxis, yaxis):
    # Return frequency parameters (frame, unit, rest frequency) from spw table
    freq_axes = ['frequency', 'velocity', 'uwave', 'vwave', 'wwave', 'uvwave']
    if xaxis in freq_axes or yaxis in freq_axes:
        spw_table = xds.SPECTRAL_WINDOW
        ref_types = spw_table.column_descriptions['CHAN_FREQ']['keywords']['MEASINFO']['TabRefTypes']
        freq_frame = ref_types[spw_table.MEAS_FREQ_REF.values[0]]
        freq_unit = spw_table.column_descriptions['CHAN_FREQ']['keywords']['QuantumUnits'][0]
        freqs = spw_table.CHAN_FREQ.values[0]
        rest_freq = freqs[int(len(freqs) / 2)]
        return freq_frame, freq_unit, rest_freq

    return "", "", None

def _setup_axis(axis):
    labels = {'uvdist': 'UVdist', 'uvwave': 'UVwave', 'wtxamp': 'Wt*Amp',
        'wtsp': 'WtSp', 'sigmasp': 'SigmaSp'}
    if axis in labels:
        label = labels[axis]
    else:
        label = axis.capitalize()

    if axis == "time":
        date_format = ['%Y-%m-%d %H:%M:%S']
        time_format = ['%H:%M:%S']
        formatter = DatetimeTickFormatter(days=date_format, months=date_format,
            years=date_format, hours=time_format, minutes=time_format, seconds=time_format)
    else:
        formatter = BasicTickFormatter()

    return (label, formatter)

def _add_axis_unit(axis_name, first_time, freq_frame):
    units = {"Interval": " (s)", "Frequency": " (GHz)", "Velocity": " (km/s)",
        "Phase": " (deg)"}
    if axis_name in units:
        label = axis_name + units[axis_name]
        if axis_name == "Frequency":
            label = label + " " + freq_frame
    elif axis_name == "Time":
        time_string = np.datetime_as_string(first_time)
        date = time_string[0 : time_string.find("T")]
        label = axis_name + " (from " + date + ")"
    elif axis_name in ["U", "V", "W", "UVdist"]:
        label = axis_name + " (m)"
    elif axis_name in ["Uwave", "Vwave", "Wwave", "UVwave"]:
        label = axis_name + " (\u03BB)"
    else:
        label = axis_name

    return label

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
    # Coordinates: remove uvw_index since already indexed to get u, v, w
    xdims = tuple(dim for dim in _get_array_dims(xds, xkey) if dim != 'uvw_index')
    ydims = tuple(dim for dim in _get_array_dims(xds, ykey) if dim != 'uvw_index')
    plot_dims = set(xdims + ydims)
    plot_coords = {}
    for dim in plot_dims:
        plot_coords[dim] = xds.coords[dim]

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
        # Axis calculated from two values
        dims0 = _get_array_dims(xds, key[0])
        dims1 = _get_array_dims(xds, key[1])
        if dims0 == dims1:
            return dims0
        elif set(dims0).issubset(dims1):
            return dims1
        elif set(dims1).issubset(dims0):
            return dims0
        else:
            # uwave, vwave, wwave (UVW, chan) put chan first
            return dims1 + dims0
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
    if key == "UVW":
        if axis in ["u", "uwave"]:
            return xda.sel(uvw_index=0).values
        if axis in ["v", "vwave"]:
            return xda.sel(uvw_index=1).values
        if axis in ["w", "wwave"]:
            return xda.sel(uvw_index=2).values
        if axis in ["uvdist", "uvwave"]:
            u = xda.sel(uvw_index=0).values
            v = xda.sel(uvw_index=1).values
            return np.sqrt(u*u + v*v)
    elif key == "DATA":
        if axis in ["amp", "wtxamp"]:
            return np.abs(xda.values)
        if axis == "phase":
            return np.angle(xda.values) * 180.0 / np.pi
        if axis == "real":
            return np.real(xda.values)
        if axis == "imag":
            return np.imag(xda.values)
    elif key == "chan":
        if axis == "channel":
            return np.array(range(xda.values.size))
    elif key == "FLAG":
        return xda.values.astype(int)

    return xda.values

def _get_calc_values(xds, key, axis):
    # axis calculated from two values
    if (len(key) < 2):
        raise RuntimeError(f"Cannot calculate {axis} from one column")

    data0 = _get_data(xds, key[0], axis)
    data1 = _get_data(xds, key[1], axis)

    if axis == "wtxamp":
        # data0=WEIGHT, data1=AMP.  Multiply each channel plane by weight matrix
        for i in range(xds.dims['chan']):
            data1[:,i,:] *= data0
        return data1
    elif axis == "baseline":
        # data0=ANTENNA1, data1=ANTENNA2
        num_ant = max(max(data0), max(data1)) + 1
        return np.array([(num_ant + 1) * ant1 - (ant1 * ant1 + 1) / 2 + ant2 for ant1, ant2 in zip(data0, data1)])
    elif "wave" in axis:
        # data0=U/V/W/UVDIST (row), data1=FREQ (chan)
        wave = np.zeros(shape=(xds.dims['chan'], xds.dims['row']))
        for i in range(xds.dims['row']):
            wave[:, i] = (data0[i] / constants['c'].get_value()) * (data1)
        return wave
    else:
        raise RuntimeError(f"axis {axis} not supported")

def _get_data(xds, key, axis):
    if isinstance(key, tuple):
        return _get_calc_values(xds, key, axis)
    else:
        xda = _get_array(xds, key)
        return _get_values(xda, key, axis)

def _calc_freq(xds, freq_unit):
    if freq_unit != "GHz":
        freqs = xds.frequency.values
        dm = measures()
        freqs_GHz = []

        for freq in freqs:
            freq_quant = quantity(freq, freq_unit)
            freqs_GHz.append(freq_quant.get_value('GHz'))

        xds.frequency.values = np.array(freqs_GHz)

def _calc_velocity(xds, freq_frame, freq_unit, rest_freq):
    freqs = xds.velocity.values
    dm = measures()
    velocities = []
    rf = dm.frequency(freq_frame, quantity(rest_freq, freq_unit))

    for freq in freqs:
        f = dm.frequency(freq_frame, quantity(freq, freq_unit))
        v = dm.todoppler('radio', f, rf)['m0']
        vq = quantity(v['value'], v['unit'])
        velocities.append(vq.get_value('km/s'))

    xds.velocity.values = np.array(velocities)

def _save_plot(plotfile, plot):
    print("Saving plot to", plotfile)

    if plotfile.endswith(".png"):
        # hvplot adds HSpacers with stretch_width to hv.DynamicMap
        # (datashader plot), producing very wide png with centered plot.
        # Using workaround in https://github.com/holoviz/holoviews/issues/4489
        #hvplot.save(plot, plotfile)
        pn.pane.HoloViews(plot.options(toolbar=None)).save(plotfile)
    elif plotfile.endswith(".svg"):
        # FIXME: svg plot has axes but no points; show(bokeh_plot) is ok
        bokeh_plot = hv.render(plot)
        bokeh_plot.output_backend = "svg"
        export_svgs(bokeh_plot, filename=plotfile)
    elif plotfile.endswith(".pdf"):
        if _have_svg2pdf:
            # FIXME: svg plot has axes but no points; show(bokeh_plot) is ok
            bokeh_plot = hv.render(plot)
            bokeh_plot.output_backend = "svg"
            export_svgs(bokeh_plot, filename='tmp.svg')
            svg2pdf(url="tmp.svg", write_to=plotfile)
            os.system("rm tmp.svg")
        else:
            raise RuntimeError("Could not import cairosvg for PDF export")
    else:
        raise ValueError("Invalid output file extension type.  Must be png, svg or pdf")

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
        Filename for exported plot. Currently only .png supported.
    showplot (bool):
        Whether to show interactive plot in browser tab

    Axis options:
        NOTE: Items in parentheses not implemented yet
        METADATA
            scan, field, time, interval, spw, channel, frequency,
            velocity, corr, antenna1, antenna2, baseline, corr, antenna1,
            antenna2, baseline, observation, intent, feed1, feed2
        VISIBILITIES and FLAGS
            amp, phase, real, imag, weight, wtxamp, wtsp, sigma, sigmasp, flag
        OBSERVATIONAL GEOMETRY
            u, v, w, uvdist, uwave, vwave, wwave, uvwave,
            (azimuth), (elevation), (hourang), (parang)
        ANTENNA-BASED GEOMETRY
            (antenna), (ant-az), (ant-el), (ant-ra), (ant-dec), (ant-parang)
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
                 'velocity': 'chan',
                 'corr': 'pol',
                 'antenna1': 'ANTENNA1',
                 'antenna2': 'ANTENNA2',
                 'baseline': ('ANTENNA1', 'ANTENNA2'),
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
                 'wtxamp': ('WEIGHT', 'DATA'),
                 'wtsp': 'WEIGHT_SPECTRUM',
                 'sigma': 'SIGMA', 
                 'sigmasp': 'SIGMA_SPECTRUM', 
                 'flag': 'FLAG',
                 # OBSERVATIONAL GEOMETRY
                 'u': 'UVW',
                 'v': 'UVW',
                 'w': 'UVW',
                 'uvdist': 'UVW',
                 'uwave': ('UVW', 'chan'),
                 'vwave': ('UVW', 'chan'),
                 'wwave': ('UVW', 'chan'),
                 'uvwave': ('UVW', 'chan'),
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

    uvw = ['u', 'v', 'w']
    is_uv_plot = xaxis in uvw and yaxis in uvw

    # Read ms into xarray dataset
    print("Reading MeasurementSet")
    ms_xds = read_ms(infile=vis)

    # Extra info for plotting certain axes
    plot_width = _PLOT_WIDTH
    plot_height = _PLOT_WIDTH if is_uv_plot else _PLOT_HEIGHT
    first_time = ms_xds.xds0.TIME.values[0]
    freq_frame, freq_unit, rest_freq = _get_freq_params(ms_xds, xaxis, yaxis)

    # Set up axis labels and plot title (with simple axis labels)
    xlabel, xformatter = _setup_axis(xaxis)
    ylabel, yformatter = _setup_axis(yaxis)
    if not title:
        msname = os.path.basename(vis)
        title = msname + "\n" + ylabel + " vs. " +  xlabel

    xlabel = _add_axis_unit(xlabel, first_time, freq_frame)
    ylabel = _add_axis_unit(ylabel, first_time, freq_frame)

    xkey = axis_keys[xaxis]
    ykey = axis_keys[yaxis]

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

        if "frequency" in plot_xds.data_vars:
            # Convert to GHz
            _calc_freq(plot_xds, freq_unit)
        if "velocity" in plot_xds.data_vars:
            # Convert freq to velocity km/s
            _calc_velocity(plot_xds, freq_frame, freq_unit, rest_freq)

        # Convert to dataframe and plot
        plot_df = plot_xds.to_dataframe()
        plot = plot_df.hvplot.scatter(xaxis, yaxis,
            title=title, xlabel=xlabel, ylabel=ylabel,
            xformatter=xformatter, yformatter=yformatter,
            width=plot_width, height=plot_height,
            rasterize=True, cmap=['blue'], padding=(0.01, 0.01), hover=True)

        if spw == 0: layout = plot
        else:        layout = layout * plot

        if is_uv_plot:
            # plot conjugates
            conj_plot_df = plot_df * -1.0
            plot = conj_plot_df.hvplot.scatter(xaxis, yaxis,
                title=title, xlabel=xlabel, ylabel=ylabel,
                xformatter=xformatter, yformatter=yformatter,
                width=plot_width, height=plot_height,
                rasterize=True, cmap=['blue'], padding=(0.01, 0.01), hover=True)
            layout = layout * plot

    if showplot:
        print("Showing plot")
        hvplot.show(layout, title='PlotMS', threaded=True)

    if plotfile != "":
        _save_plot(plotfile, layout)
