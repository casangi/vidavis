.. _design-usage-settings:

Usage Settings
==============

In addition to the desire to have a single implementation to provide the core visualization
functionality, there are four settings where the single Python implementation will have
to function. All of the vidavis functionality will **not** be available in all of these
settings, but some subset will be available in all settings. The limits on applicability
come from setting limitations (headless operation precludes direct user interaction) as
well as platform limitations (Jupyter notebook model centers around evaluating a cell and
receiving a response). We navigate these limitations as the vidavis system is built out
with new GUI elements. The rest of this section will outline the usage settings for the
vidavis system.

Headless
^^^^^^^^^^^^^^^^^

.. image:: _static/headless_model.svg
           :align: left
           :width: 60px

In many applications, user interaction is not possible. A display may not exist or it may
not be accessible. One important area that the vidavis system must support is pipeline
processing of data collected from radio telescopes. This processing happens after the data
is collected by the online system and it generates the observation artifacts that are
provided to investigators.

In the headless setting, the only process involved from the vidavis perspective is the
Python process that imported the vidavis Python package, and the only display option
available is the generation of raster files (png, jpg, etc.).

Terminal
^^^^^^^^^^^^^^^^


.. image:: _static/terminal_model.svg
           :align: left
           :width: 160px

The terminal setting is the typical Python usage setting. In this case, the user interacts
with Python interactively, e.g. with IPython, or by running Python scripts from a terminal.
A display is available, but no other support processes are available. The user installs
the vidavis package into their python environment using something like pip.  Because we
want to avoid OS specific binary applications, all vidavis functionality in this setting is
implemented in Python, and the frameworks which are leveraged in the implementation are
also in Python. These individual frameworks may provide OS-specific implementations, but
the vidavis Python package is isolated from the incompatibilities which such implementations
entail.

In the terminal setting, the user’s web browser is the best display option. It is (hopefully)
compatible with the vidavis application framework, and the user already has a browser that
they use that is suitable for display. It is possible that some Python visualization packages
also include a server for displaying information, and in some cases, this may be the only
option. However, the only processes that are available in the terminal setting are those
that the user is expected to have (browser) and those that come with standard Python packages.

Application
^^^^^^^^^^^^^^^^

.. image:: _static/application_model.svg
           :align: left
           :width: 180px

The application setting is in some respects a new setting for CASA. Although CASA has had
applications in the past, for example casaviewer, casaplotms, etc., these have been
purpose-built applications that were implemented separately from the main CASA Python
application. Typically, these applications leveraged some portion of the C++ code that
underlies the implementation of the casatools. This implementational separation from Python
made it difficult to implement a Python scripting interface for the purpose-built, stand-alone
applications.

The vidavis system takes a different approach. The vidavis Python package and its application
framework, Electron, are leveraged to create a platform for hosting all of the visualization
applications in the vidavis system. All of these applications will be hosted by a single, running
instance of the application framework. This is possible because the framework is built on Chromium,
the same application framework that underlies the Google Chrome browser.

In the application setting, we have much more flexibility and control than in any of the other
settings. Here we leverage the Jupyter Protocol and the IPython kernel that goes along with it.
The **same** vidavis python package used in the other settings is imported into the IPython
kernel and generates the visualization elements that go into producing standalone applications.
These applications are too complex to be implemented using currently available python frameworks.
By using Electron and the tools that are available in TypeScript/JavaScript, the same plots
that are available to users in the other settings can be incorporated into much more capable and
wide ranging applications in this setting. A plot that is generated in the headless setting for
saving to a raster file will be identical to the plot displayed in our Electron application, since
they use the same vidavis Python implementation.

Notebook
^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: _static/notebook_model.svg
           :align: left
           :width: 180px

The GUI elements available in the notebook setting will be a subset of those available in the
application setting. However, because our application framework and Jupyter notebooks share the
same underlying protocol, many of the plots generated by the common vidavis Python package will
just automatically work in the notebook setting. While notebooks are very useful for collaboration
and documentation, this is the least important of the usage settings we are targeting, but we
structured our architecture to support notebook display as much as possible.

This setting is less general than the application setting. When users interact with a Jupyter
notebook, they may not realize that there is an execution context (typically Python) underlying
the notebook web page. Here our process diagram (above) looks below the surface to expose the
similarities between the notebook setting and our application setting. They share a communication
protocol and an execution environment in common.

The notebook setting is constrained by the limitations of the Jupyter notebook architecture.
Most of the individual plots that the vidavis Python package is capable of creating should
display fine within a notebook. The very complicated applications which can be created in the
application setting will not be available in the notebook setting.
