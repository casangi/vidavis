.. _design-plotter-design:

Plotting Visibility Data
========================

.. currentmodule:: design

Overview
````````
Plotting visibility data has common functionality, whether the plot is a raster
plot, a scatter plot, or a plot of other data included in the dataset.  This
functionality exists in the code base outside of any single application.

The data interface currently supports only :xref:`xradio` ProcessingSets stored
on disk as Zarr files and opened as an :xref:`xarray` DataTree containing MSv4
DataTrees. Convenience functions have been added in the XRADIO ProcessingSetXdt
and MeasurementSetXdt classes and can be used with special accessors from the
core DataTree.

The plotting interface is based upon the :xref:`hvplot` framework with the
:xref:`bokeh` backend for creating interactive plots. The :xref:`panel`
framework is used to add interactive GUI widgets to set plot parameters. These
frameworks allow for the development of sophisticated plotting applications.
Bokeh's Python libraries generate JavaScript applications which are then
displayed in a web browser. The approach allows for the same GUIs to be used,
with minor changes, in `Jupyter Notebooks <https://jupyter.org/>`_, traditional
web sites, and in desktop applications via `Electron <https://www.electronjs.org/>`_.

Application
```````````

All plotting applications are derived from the ``MsPlot`` class, which creates
the ``MsData`` object for access to the MeasurementSet visibility data.
``MsPlot`` contains functions common to all applications with MSv4 data and
plots.

MeasurementSet Data
```````````````````

The :code:`vidavis` application prototypes are based on the :xref:`xradio`
ProcessingSet using the :xref:`schema`, but could be extended to
support MeasurementSet v2 data or other schemas. MeasurementSet data is accessed
from applications using the ``MsData`` class, which defines an interface to
ProcessingSet data in the ``PsData`` class. Additional classes could be added
here for other data formats with the package dependencies installed to read
these formats.  Many functions are available for ProcessingSet data to handle
MSv2 to MSv4 conversion, reading data and converting coordinates, performing
selection, and calculating statistics.

Plot
````

Since users often have a preference for general plot style settings, such
as a colormap, these can be set in a Plot class specific to each plot type (for
example, ``RasterPlot``), then used for each plot thereafter until changed. The
style preferences are set separately from the plot function.

Since ProcessingSet and MeasurementSet data selection includes parameters
pertaining to how the selection is done (for example, whether to match strings
partially or exactly, and the method and tolerance when selecting a float
value), the selection is also done separately from the plot function.

The Plot class for each application is responsible for creating a plot from the
selected MeasurementSet data passed to it, using the stored style settings. This
data is represented by an :xref:`xarray` object such as a Dataset. Since
:xref:`hvplot` has an Xarray extension and also supports :xref:`datashader` for
big data, this package was selected to easily make a :xref:`holoviews` plot. The
plot object is stored and can then be shown or saved, and the plot data is also
stored to be used to locate data points.

Plot objects created by the applications are stored in
a list, which can be combined in a :xref:`holoviews` Layout plot according to
user-specified rows and columns, or accessed individually. The plot may be shown
in a browser tab as a :xref:`holoviews` DynamicMap using :xref:`bokeh` and
:xref:`panel`, or saved to a file using :xref:`hvplot` or :xref:`bokeh`. The
DynamicMap is required for callbacks when plot regions (box or point) are drawn.

GUI
```

The plot is displayed in the GUI by creating a placeholder for a
:xref:`holoviews` DynamicMap, which can be updated as plot settings change and
new plots are created. The DynamicMap also supports callbacks for locating data
points.

Although the GUI widgets for plot settings are specific to the type of plot,
an interface to create common
`Panel components <https://panel.holoviz.org/reference/index.html>`_
for the GUI can be used by all applications. These high-level components can be
customized and include an easy callback implementation used when the widget
value changes.

Future Work
```````````

As described in :ref:`Usage Settings <design-usage-settings>`, the goal for the
``vidavis`` applications is to support headless, terminal, standalone
application, and notebook usage.  Currently, only headless and terminal usage
are supported. In addition, remote execution, in which the Python terminal is
run on a remote machine and the plot is shown on the local browser, would be
desirable.

``vidavis`` contains one application, ``MsRaster``, for creating visibility
raster plots. Eventually, visibility scatter plots will be supported with the
``MsScatter`` application. Both applications should support a :xref:`casa` MSv2
data source. An MSv4 interface to MSv2 files is currently under investigation in
XRADIO, and this should be added to ``vidavis`` when available.

While :xref:`casa` continues to be the primary data reduction
package for MSv2 data, exporting the MSv4 flags not only to the Zarr file but
also to a file to be used by the
`flagdata <https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.flagging.flagdata.html#casatasks.flagging.flagdata>`_
task in manual mode should be implemented.
