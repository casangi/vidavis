.. _design-plotter-design:

Plotting Visibility Data
========================

.. currentmodule:: design

Overview
````````
Plotting visibility data has common functionality, whether the plot is a raster
plot, a scatter plot, or a plot of other data included in the dataset.  This
functionality exists in the code base outside of any single application.

The plotting interface is based upon the :xref:`hvplot` framework with the
:xref:`bokeh` backend for creating interactive plots. The :xref:`panel`
framework is used to add interactive GUI widgets to set plot parameters. These
frameworks allow for the development of sophisticated plotting applications.
Bokeh's Python libraries generate JavaScript applications which are then
displayed in a web browser. The approach allows for the same GUIs to be used,
with minor changes, in `Jupyter Notebooks <https://jupyter.org/>`_, traditional
web sites, and in desktop applications via `Electron <https://www.electronjs.org/>`_.

MeasurementSet Data
```````````````````

The :code:`vidavis` application prototypes are based on the :xref:`xradio`
ProcessingSet using the MeasurementSet schema v4.0.0, but could be extended to
support MeasurementSetv2 data or other schemas. MeasurementSet data is accessed
from applications using the ``MsData`` class, which defines an interface to
ProcessingSet data in the ``PsData`` class. Additional classes could be added
here for other data formats with the package dependencies installed to read
these formats.  The data classes handle converting MSv2 to MSv4, reading data,
and performing selection and calculations on the data.

Application
```````````

All plotting applications are derived from the ``MsPlot`` class, which creates
the ``MsData`` object for access to the MeasurementSet data and for the
metadata-based functions. Plot objects created by the application are stored in
a list, which can be combined in a :xref:`holoviews` Layout plot according to
user-specified rows and columns, or accessed individually. The plot may be shown
in a browser tab using :xref:`bokeh`, or saved to a file using :xref:`hvplot`.

Plot
````

Since users often have a preference for general raster plot style settings, such
as a colormap, these can be set in a Plot class specific to each plot type, then
used for each plot thereafter until changed.

The Plot class for each application is responsible for creating a plot from the
MeasurementSet data passed to it, using the stored style settings. This data is
represented by an :xref:`xarray` object such as a Dataset or DataTree. Since
:xref:`hvplot` has an Xarray extension and also supports :xref:`datashader` for
big data, this package was selected to easily make a :xref:`holoviews` plot.
The plot object is stored and can then be shown or saved.

GUI
```

The plot is displayed in the GUI by creating a placeholder for a
:xref:`holoviews` DynamicMap, which can be updated as plot settings change and
new plots are created.

Although the GUI widgets for plot settings are specific to the type of plot,
an interface to create common :xref:`panel` components for the GUI can be used
by all applications. These high-level components can be customized and include
an easy callback implementation used when the widget value changes.

Future Work
```````````
The fundamental work that remains for the ``vidavis`` applications involves
using the `IPython Jupyter Kernel <https://ipython.readthedocs.io/en/stable/install/kernel_install.html>`_
as the process which runs the application. This seems like it should be possible
with no significant, known problems. Early in our abbreviated trade study, we
tested this with a simpler example (:code:`plotants`) without significant
issues. Making this functionality available means that the applications could be
used from a Jupyter Notebook or integrated into a stand-alone, desktop app based
on `Electron <https://www.electronjs.org/>`_. Both of these usage settings were
tested in the trade study. The final step, which was not tested in the trade
study, is executing an application in a **remote** IPython Kernel. The
documentation indicates that this should be possible. Once this is available, it
will be possible to start a desktop application which runs the ``vidavis``
application in a remote kernel executing on an NRAO cluster (or other compute
resource).
