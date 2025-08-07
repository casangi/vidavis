vidavis - VIsibility DAta VISualization
=======================================

This is a **pre-alpha** package. All applications are in various phases of
*prototyping*.

Introduction
------------

This package currently requires the visibility data to conform to the
`XRADIO <https://xradio.readthedocs.io/en/latest/>`_ MeasurementSet v4.0.0
schema, input as a Zarr file path which is read into an Xarray-based XRADIO
ProcessingSet. Input MSv2 file paths will be automatically converted to MSv4
zarr files with default partitioning if the necessary packages are found (see
Requirements).

The `Bokeh <https://bokeh.org/>`_ plots are created with
`hvPlot <https://hvplot.holoviz.org/>`_ and optionally shown in a
`Panel <https://panel.holoviz.org/>`_-based GUI.

The first application added to **vidavis** is **MsRaster**, which creates raster
plots of visibility data.  See example below.

Installation
------------

vidavis is available `from PyPI <https://pypi.org/project/vidavis/>`_.

Requirements
````````````

- Python 3.11 or greater

- Optionally `python-casacore <https://pypi.org/project/python-casacore/>`_ or
  `casatools <https://pypi.org/project/casatools/>`_ for MSv2 conversion

Install
```````

- :code:`pip install vidavis`

MSv2 Conversion
^^^^^^^^^^^^^^^

To enable conversion from MSv2 to MSv4 with **python-casacore** use (this only works for Linux):

- :code:`pip install "xradio[python-casacore]"`

On macOS it is required to pre-install `python-casacore` using:

- :code:`conda install -c conda-forge python-casacore`

Simple MsRaster Usage Example
`````````````````````````````

A simple example using the MsRaster application to create visibility raster plots::

  >>> from vidavis.apps import MsRaster
  >>> msr = MsRaster(ms=myms)
  >>> msr.plot() # default time vs. baseline plot
  >>> msr.show() # open plot in default browser tab
