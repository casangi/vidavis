.. _design-system-design:

System Design
=============

.. currentmodule:: design

This design document describes the history, motivation and design of the
:code:`vidavis` package, which allows the same Python functions to generate plot
files for pipeline use and interactive plots for Python users, along with the
visualization components that are included in web-based applications. Having a
single implementation ensures consistency and minimizes development and
maintenance.

Traditional Approach
--------------------

In the past our GUIs have been very big C++/`Qt <https://www.qt.io/>`_
applications which were monolithic, difficult to make script-able and complex to
maintain. They were monolithic because at the time when Qt was adopted, having
one GUI library that could be built on different platforms and work with
different windowing systems was a big advance. To accomplish this task, an
entire, low-level GUI widget library was created. Applications built upon it
needed to be built for each platform even though the Qt framework was portable.
These applications were stand-alone processes and because of this, they were
completely independent of the Python interpreter's process environment. All
*scripting* needed to be done by sending messages between the Python environment and
the compiled C++ application.

Framework Approach
------------------

To avoid these problems, we are attempting to take a new, modern approach:

#. Use a framework that is implemented in **pure-Python**

#. Use a development framework that provides **higher level functionality**
   instead of low level widgets

#. Create **reusable tools** instead of specific applications

#. Use a framework that is **web-centric**

A *pure-Python* implementation means that the applications we produce will work
in a similar way everywhere Python is available.  Direct integration with Python
also means that we will not experience all of the hurdles we have faced
attempting to make the existing CASA GUIs scriptable. It also means that a
packaging and distribution mechanism exists to allow users to easily install the 
package *along with all of its dependencies*. Better integration with the Python
ecosystem also means that things that are currently done in C++ code that CASA
developers maintain can instead be done using Python code that is maintained by
the Python community. This is a gradual process, so over time we *should* reap
greater rewards as our integration increases.

By choosing a framework that already provides the *higher level functionality*
that we require, we can avoid implementing each part of the interface at a fine
level of detail. Because it is written in Python, the interface is also
specified at a higher level of abstraction than the C++ equivalent. To avoid
creating monolithic applications, we need to look for opportunities to
*create reusable tools* that can be used by a variety of applications. This
allows multiple end-user applications to share a common set of components, but
it also should extend the development framework in ways that customize it to
our domain.

By choosing a *web-centric* framework, we gain portability and generality.
Modern web browsers are self-contained visualization environments that are
available on all platforms. Using this instead of a large development library
like `Qt <https://www.qt.io/>`_ frees us from the need to compile our
application for each platform. It also increases our portability beyond
just platform portability. By using a web-centric framework, it is much
easier to make our GUIs available in
`Jupyter Notebooks <https://jupyter.org/>`_ or as a part of websites. This
allows our applications to reach a wide variety of users.

While the advantages of this approach to GUI development vastly outweighs
the disadvantages, there are disadvantages. Free-standing applications are
set apart for desktop users by their nature. Mixing the vidavis GUIs in with all
of the other things that are done with web browsers causes the GUI to be
another tree in the forest. There are also performance ramifications. Due
in large part to all of the overhead, purpose-built, compiled applications
are very fast compared with just-in-time, on-the-fly web-centric applications
because much code is compiled dynamically as the application is loaded.
Using the framework directly from a Python interpreter depends on using
the web browser that is running on the same host. This is inconvenient
for remote use (user logs into a system and runs Python) because the web
browser must be displayed remotely with VNC or X11. This particular
problem can be resolved by using `Electron <https://www.electronjs.org/>`_
to create an application that runs on the user's local host with the
application controlling a Python kernel running on the remote host in
a model similar to Jupyter Notebooks.

Usage Settings
--------------

Users can interact with :code:`vidavis` in various settings, including headless,
terminal, application, and notebook.  These usage settings are described in more
detail separately.

.. toctree::
   :maxdepth: 3

   usage_settings

Design Documents
------------------

.. toctree::
   :maxdepth: 3

   visibility_plotting
   applications/ms_raster
   ../python/index
