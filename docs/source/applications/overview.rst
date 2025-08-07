
Overview
========

.. currentmodule:: applications

The data for the ``vidavis`` applications must be in the MeasurementSet v4.0.0
zarr format, or MeasurementSet v2 format which will be automatically converted
to MeasurementSet v4 if the necessary packages are installed.

.. _infrastructure:

Infrastructure
--------------

The applications utilize the :xref:`bokeh` backend for the plots.  Bokeh
provides built-in plot tools allowing the user to zoom, pan, select regions,
inspect data values, and save the plot. Additional libraries are used for
data I/O, logging, plotting, and interactive dashboards:

.. list-table::
   :class: borderless
   :align: center

   * - .. image:: _static/bokeh_logo.svg
          :width: 100
     - .. image:: _static/xradio_logo.webp
          :width: 100
     - .. image:: _static/graphviper_logo.jpeg
          :width: 100
     - .. image:: _static/hvplot.png
          :width: 60
     - .. image:: _static/holoviews.png
          :width: 100
     - .. image:: _static/panel.png
          :width: 100

* :xref:`xradio` (Xarray Radio Astronomy Data I/O) implements the MeasurementSet
  v4.0.0 schema using :xref:`xarray` to provide an interface for radio astronomy
  data

* :xref:`toolviper` is used for creating the Dask.distributed client and for
  logging

* :xref:`graphviper` is used for Dask-based MapReduce to convert MSv2 datasets
  and calculate statistics

* Holoviz library :xref:`hvplot` allows easy visualization of :xref:`xarray`
  data objects as interactive :xref:`bokeh` plots

* Holoviz library :xref:`holoviews` allows the ability to easily layout and
  overlay plots

* Holoviz library :xref:`panel` streamlines the development of apps and
  dashboards for the plots

Implementation
--------------

Application Modes
`````````````````

The ``vidavis`` applications create plots for the user to view interactively or
save to disk. The applications can be used in three ways from Python:

* create plots to export to file

* create interactive Bokeh plots to show in a browser window

* use a GUI dashboard in a browser window to select plot parameters and create
  interactive Bokeh plots

Data Exploration
````````````````

:xref:`xradio` allows the user to explore MeasurementSet data with a summary of
its metadata, and to make plots of antenna positions and phase center locations
of all fields. These features can be accessed in all applications.

Installation
------------

Requirements
````````````

- Python 3.11 or greater

The required dependency packages are automatically installed with ``vidavis``,
including those listed in the :ref:`Infrastructure` section.

Optionally, :xref:`xradio` with
`python-casacore <https://casacore.github.io/python-casacore/>`_
or `casatools <https://casadocs.readthedocs.io/en/stable/api/casatools.html>`_
is required to enable conversion from MSv2 to MSv4 in the applications.

.. _install_vidavis:

Install vidavis
```````````````

You may want to use the conda environment manager from
`miniforge <https://github.com/conda-forge/miniforge>`_ to create a clean,
self-contained runtime where vidavis and its dependencies can be installed::

  conda create --name vidavis python=3.12 --no-default-packages
  conda activate vidavis

Install required packages::

  pip install vidavis

.. _install_conversion:

Install for MSv2 Conversion
```````````````````````````

To install **xradio** with **python-casacore** for MSv2 conversion::

  pip install "xradio[python-casacore]"

.. note::
   On macOS it is required to **pre-install** python-casacore using
   ``conda install -c conda-forge python-casacore``.

It is also possible to use
`casatools <https://casadocs.readthedocs.io/en/stable/api/casatools.html>`_
as the backend for reading the MSv2. See the
`XRADIO casatools setup guide <https://xradio.readthedocs.io/en/latest/measurement_set/guides/backends.html>`_
for more information.

Dask.distributed Scheduler
--------------------------

For parallel processing workflows, you can set up a local Dask cluster using
:xref:`toolviper`. Dask.distributed is a centrally managed, distributed, dynamic
task scheduler.

**Prior to** using the ``vidavis`` applications, you may elect to start a Dask
Client (local machine) or a Dask LocalCluster (cluster). For a local client, set
the number of cores and memory limit per core to use. The logging level for the
main thread and the worker threads may also be set (default "INFO"). When
plotting small datasets, however, this adds overhead which may make plotting
slower than without the client.

:xref:`toolviper` has an interface to create and access a local or distributed
client.  See the
`client tutorial <https://github.com/casangi/toolviper/blob/main/docs/client_tutorial.ipynb>`_
and ``help(local_client)`` or ``help(distributed_client)`` for more information.

.. warning::
   If Python scripts are used to make plots, the client should not be created in
   the main thread.  For more details, see
   `Standalone Python scripts <https://docs.dask.org/en/stable/scheduling.html#standalone-python-scripts>`_
   in the Dask Scheduling documentation.
