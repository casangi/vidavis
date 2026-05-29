.. _design-msraster-design:

MsRaster Design
===============

.. currentmodule:: design

``MsRaster`` is the first test of the approach described in
:ref:`visibility plotting <design-plotter-design>`. It provides an optional GUI
interface to a Python interface to create raster plots shown in a browser tab or
saved to file.

.. note::
   This design page contains detailed notes aimed at developers.

Code organization
`````````````````

The ``vidavis`` source code is divided into the broad categories (with
corresponding directory names) of **apps, data, plot, bokeh,** and **toolbox**.

* **apps**: MsRaster (future home of MsScatter as well)

* **data**:

  * **data/measurement_set**: subdirectory for MeasurementSet data

    * **data/measurement_set/processing_set**: subdirectory for ProcessingSet
      data and support functions

  * data subdirectories allow addition of other types of data, e.g. calibration
    tables

  * measurement_set subdirectories allow addition of other formats of data, e.g.
    casatools interface

* **plot**: 

  * **plot/ms_plot**: subdirectory for MeasurementSet plots and support functions

* **bokeh**: Color palette (common with ``cubevis``)

* **toolbox**: AppContext (common with ``cubevis``)

MsRaster Data
`````````````

* Abbreviations:

  * ps : ProcessingSet

  * ms : MeasurementSet

  * xdt : Xarray DataTree

  * xds : Xarray Dataset

  * xda : Xarray DataArray

MsRaster only supports XRADIO ProcessingSet Zarr files. If an MSv2 path is
provided, the MSv2 is converted to MSv4 in the same directory using the XRADIO
conversion function with default partitioning. The Zarr file is lazily opened
with only the metadata, returning an Xarray DataTree in the ProcessingSet schema
(**ps_xdt**), which contains MSv4 Xarray DataTrees (**ms_xdt**).

These MSv4s are the MSv2 partitioned when the Zarr file was created. The
default partitioning is **data description** (spectral window and polarization
setup) and **obs mode** (intent?).

On disk, the Zarr file is a directory, and each subdirectory is an MSv4 name.
Each directory contains .zattrs and .zmetadata, where .zattrs contains the
DataTree attributes and .zmetadata contains the consolidated attributes of
subtrees. This is important to understand when writing to zarr (as in
flagging); each ms_xdt must be written to zarr to write the new data group
attributes, then the ps_xdt must be written to zarr to consolidate these new
attributes at the ProcessingSet level. Besides these dot files, the MSv4
directories contain directories for each coordinate and data variable.

* Accessors:

  * ps_xdt : Xarray `DataTree
    <https://docs.xarray.dev/en/latest/api/datatree.html>`_ returned from
    ``open_processing_set``

  * ps_xdt.xr_ps : XRADIO `ProcessingSetXdt
    <https://xradio.readthedocs.io/en/latest/measurement_set/api.html#processingsetxdt-api>`_

  * ps_xdt[ms_name] = ms_xdt : Xarray `DataTree
    <https://docs.xarray.dev/en/latest/api/datatree.html>`_

  * ms_xdt.xr_ms : XRADIO `MeasurementSetXdt
    <https://xradio.readthedocs.io/en/latest/measurement_set/api.html#measurementsetxdt-api>`_

  * ms_xdt.ds : correlated data Xarray `Dataset
    <https://docs.xarray.dev/en/latest/api/dataset.html>`_ (a **read-only** DatasetView)

  * ms_xdt.name or ms_xdt[name] : Xarray `DataArray
    <https://docs.xarray.dev/en/latest/api/dataarray.html>`_ for the coordinate
    or data variable name

      * xarray.DataArray.values = np.ndarray

      * xarray.DataArray.data = array of underlying type (e.g. dask.Array)

To understand the data schema, it is highly recommended to review the examples
in the XRADIO `MeasurementSet tutorial
<https://xradio.readthedocs.io/en/latest/measurement_set/tutorials/measurement_set_tutorial.html>`_.
Each ms_xdt contains dimensions, coordinates, data variables, and attributes.
Dimensions are named or labeled 1-dimensional coordinate arrays, so data
values are accessed using the dimension label rather than by an index (for
example, a polarization dimension would be accessed using "XX" rather than
index 0). Coordinates are Xarray DataArrays, which may or may not be dimensions
(signified with a ``*``). Data variables are multidimensional Xarray DataArrays.
These DataArrays have attribute dictionaries holding arbitrary metadata
describing the data (for example, units).

MeasurementSet DataTrees can contain multiple sets of VISIBILITY, FLAG, WEIGHT,
and UVW data variables. To maintain the relationship between these variables,
the ms_xdts have a "data_groups" attribute. Each data group is a
dictionary of "correlated_data", "flag", "weight", and "uvw". The "base" data
group has VISIBILITY correlated data which corresponds to the DATA column in an
MSv2. There may also be VISIBILITY_CORRECTED and VISIBILITY_MODEL data variables
in "corrected" and "model" data groups (same flag, weight, etc.). The default
data group is "base".

It is easy to see that these data variables can be in multiple data groups, such
as when flags are manually set or weights are modified during calibration. All
that is required is creating a new data group with the keyword updated to the
new data variable, selecting the data group, and plotting it. In fact, this is
how MsRaster flagging is done.

.. warning::
   When a data_group is selected using XRADIO ProcessingSetXdt.query(), the
   data group is selected in the ms_xdts in the processing set not only in the 
   returned ps_xdt but also in the source ps_xdt. For example, after
   ``selected_ps=ps_xdt.query(data_group_name='corrected')`` the selected_ps
   **and** ps_xdt both contain only the corrected data group and an error
   results from selecting another data group
   ``selected_ps2=ps_xdt.query(data_group_name='model')``. To restore all data
   groups for selection, recreate the ps_xdt using ``open_processing_set``.

Visibility data has four dimensions: time, baseline_id, frequency, and
polarization.

  * time (float64): MsRaster converts to datetime64 using the time DataArray
    attributes.

  * baseline_id (int64): each id is an index into baseline_antenna1_name and 
    baseline_antenna2_name in MSv4 correlated data. The ids are not consistent
    across ms_xdts and a specific id may identify different antenna pairs in
    different ms_xdts. Because of this, MsRaster creates a 'baseline' coordinate
    consisting of the antenna names "ant1 & ant2", indexes a list of all antenna
    pairs in all ms_xdts, sorts them, and assigns a consistent baseline_id
    coordinate. This is necessary since all selected MSv4s are concatenated into
    a single Xarray Dataset for plotting, so the baseline id must be
    consistent.

  * frequency (float64): units are described in this DataArray's attributes,
    usually "Hz". If the frequencies are in the GHz range then the values are 
    converted to GHz and the units are updated accordingly. For consistent
    data shapes, if the user has not selected a spectral window, the first spw
    (at the minimum time) is automatically selected.

  * polarization (unicode string): polarization labels rather than ids. For a
    plot axis, ids are assigned to the polarizations in casacore Stokes order.

The user selects which two dimensions will be the x- and y-axes of the plot
(default time vs. baseline). Numeric dimensions can easily be used as axes, but
string dimensions must have an index assigned. The index DataArray becomes the
dimension, and the string coordinate labels are used for the axis tick labels.

Since visibility data is 4D and raster plot data is 2D, the dimensions which
are not plot axes must be selected or aggregated. MsRaster allows the user to
specify this selection or aggregation, else the "first" values are selected
automatically. For numeric dimensions, the "first" value is the minimum value in
the plot data. Polarization labels are assigned the enum value listed in
casacore Stokes.h, then the minimum enum value is used to select its
corresponding label. For example, in a time vs. baseline plot, the first
frequency and polarization are automatically selected.

The 2D data in all MSv4s is concatenated into one Xarray Dataset, then the 
complex component for the selected "vis_axis" is applied to the visibility
DataArray indicated by the data group "correlated data". Note that the
coordinates and data variables in the Dataset, which are stored in Dask
arrays, are *lazily* evaluated and only computed when the plot is shown or
saved. For this reason, creating a plot is very fast but show() and save()
are slower while selection and calculations are performed in a dask graph.

However, the values computed for the plot are then discarded and must be
recomputed when accessed again. To locate a point in the plot (e.g. the cursor
position) the values shown in Cursor Location must be computed again. To avoid
this, one could compute the Xarray DataArrays in the Dataset (xda.compute()),
but this puts the calculated data in a numpy array in memory. This approach
would not work where the data would not fit in memory.

Plot
````

Raster plots are created in a ``RasterPlot`` class using the supplied raster
Xarray Dataset and the stored style parameters (e.g. colormaps). First, a plot
is created for the visibility DataArray with the unflagged colormap, then a new
Xarray DataArray is created for flagged data (VISIBILITY where FLAG==1); values
are nan where FLAG==0. A second plot is created using the flagged colormap.
The data plot is overlaid by the flagged plot in a :xref:`holoviews` Overlay
plot object which is returned to the application.

The Overlay plot is stored in a list; additional plots may be added to the list
using iteration or clear_plots=False. The list of plots may then be combined in
a :xref:`holoviews` Layout according to the number of rows and columns.

Plot operators:

  * overlay = plot1 * plot2

  * layout = plot1 + plot2

GUI
```

The GUI is created in ``MsRaster`` using a :xref:`holoviews` DynamicMap
placeholder for the plot and common `Panel components
<https://panel.holoviz.org/reference/index.html>`_ arranged in Panel
tabs, rows and columns. The components are created with callbacks to MsRaster
and MsPlot methods by adding the callback to the layout where the user input
is located.

Locating the cursor, points, and boxes utilizes holoviews
`streams <https://holoviews.org/reference/index.html#streams>`_. These streams
are added to the DynamicMap plot to enable the callbacks to locate the values
in each stream. The values passed to the callback functions are the coordinate
values in the plot Dataset.

For all callbacks, the GUI is not updated until the callback function returns
(see Future Work refactoring below).

Future Work
```````````

* Data

  * Support MSv2 without conversion. See issue in XRADIO where an MSv4 interface
    is added to MSv2 so that a ProcessingSet can still be used.

* Documentation

  * MsRaster API requested

* Refactoring

  * MsPlot: too much implementation code added here, features (locate, flagging)
    should be moved to another file or class. Some code will probably be raster
    plot-specific (which will be apparent when scatter plots are added) and
    should be moved from MsPlot to MsRaster or elsewhere.

  * Locate: To the user, it looks like nothing is happening in the GUI until all
    points are located, rather than filling in one by one. When flagging, locate
    must finish before flag button is enabled. This is poor user experience and 
    should be done in a separate thread.

* Plotting

  * Rasterize: hvplot supports plotting with ``rasterize=True``, but this caused
    an error in MsRaster (xda.hvplot(..., rasterize=True) in _raster_plot.py).
    Not sure why. This would be important for future datasets with large time,
    baseline, or frequency axes.

    * ``datashade=True`` returns RGB object instead of points (r, g, b in hover)

    * ``rasterize=True`` returns aggregate object instead of points (x, y, count
      in hover, maybe you can select another aggregator besides count)

* Flagging

  * More testing needs to be done
  * Flags only written to Zarr file. Need manual flagging to be available to
    apply to MSv2 by writing selection strings to file. See casadocs `flagdata
    <https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.flagging.flagdata.html#casatasks.flagging.flagdata>`_
    documentation describing mode='list' with inpfile (?).

* Weights

  * Not used in any aggregation, for example mean is the Xarray Dataset mean()
    of the visibility data along the specified data dimension

* Performance

  * Setting up toolviper Dask client is key (perhaps beyond scope of vis
    plotting). Will be more critical for scatter plots which use much more
    data; a scatter plot could include **all** visibility data in the processing
    set e.g. amp vs time plot.

  * Dask `diagnostic dashboard <https://docs.dask.org/en/stable/dashboard.html>`_

  * Dask `local diagnostics <https://docs.dask.org/en/stable/diagnostics-local.html>`_

* Usage modes

  * So far, only done from Python session. Have not tested demo scripts lately.

  * Notebook:

    * hvplot: https://hvplot.holoviz.org/en/docs/latest/user_guide/Viewing.html#notebook

    * holoviews: https://holoviews.org/user_guide/Deploying_Bokeh_Apps.html

* Scatter plots

  * While raster plots use dimensions as plot axes, scatter plots can use any
    coordinate or data variable as axes. These axes can have different and even
    unrelated dimensions. The easiest way to create (x,y) points is to convert
    the Xarray Dataset to a Pandas dataframe with tabular data. However, Pandas
    DataFrames are in-memory data structures and can throw MemoryError
    exceptions. Possibly plot subsets of data and combine in overlay?

  * Use Datashader for these large plots -- see how Datashader solves `Plotting
    Pitfalls <https://datashader.org/user_guide/Plotting_Pitfalls.html>`_.
    Datashader is part of the Holoviz libraries including hvPlot, Holoviews,
    and Panel.
