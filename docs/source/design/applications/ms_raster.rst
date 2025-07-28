.. _design-msraster-design:

MsRaster Design
===============

.. currentmodule:: design

``MsRaster`` is the first test of the approach described in
:ref:`visibility plotting <design-plotter-design>`. It provides an optional GUI
interface to a Python interface to create raster plots in a browser tab or
saved to file.


MeasurementSet Data
```````````````````

ProcessingSet data is prepared for raster plotting by selecting or aggregating
the axes not being plotted, calculating the complex component if needed, then
concatenating the the MeasurementSet Xarray Datasets into a single DataSet with
the visibility data in a single DataArray.

Note that this data, which is stored in a Dask array, is *lazily* evaluated
until the plot is shown or saved. At this point, data is read from disk and
calculations are performed in a dask graph. For this reason, creating a plot is
very fast.

Plot
````

Raster plots are created in a ``RasterPlot`` class using the supplied raster
:xref:`xarray` Dataset, the stored style parameters, and the user inputs for the
plot. :xref:`xarray` DataArrays are created for flagged and unflagged data,
plotted separately with different colormaps, then overlaid in a
:xref:`holoviews` Overlay plot object which is returned to the application.

These overlay plots are stored in a list, where they can be combined in a layout
if requested then shown and saved as implemented in the base ``MsPlot`` class.

GUI
```

The GUI is created in ``MsRaster`` using a :xref:`holoviews` DynamicMap
placeholder and common :xref:`panel` components arranged in Panel rows and
columns. The components are created with callbacks to MsRaster methods to store
the plot inputs. When the *Plot* button is clicked, the new plot is created
according to the inputs and returned to the DynamicMap to be shown in the GUI.
