'''
Base class for ms plots
'''

import os
import time

from bokeh.io import export_png, export_svg
from bokeh.plotting import save, show
import hvplot
import holoviews as hv
import numpy as np
import panel as pn
from selenium import webdriver

try:
    from toolviper.utils.logger import get_logger, setup_logger
    _HAVE_TOOLVIPER = True
except ImportError:
    _HAVE_TOOLVIPER = False

from vidavis.data.measurement_set._ms_data import MsData
from vidavis.toolbox import AppContext, get_logger

class MsPlot:

    ''' Base class for MS plots with common functionality '''

# pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(self, ms=None, log_level="info", log_to_file=False, show_gui=False, app_name="MsPlot"):
        if not ms and not show_gui:
            raise RuntimeError("Must provide ms/zarr path if gui not shown.")

        # Set logger: use toolviper logger else casalog else python logger
        if _HAVE_TOOLVIPER:
            self._logger = setup_logger(app_name, log_to_term=True, log_to_file=log_to_file, log_file=app_name.lower(), log_level=log_level.upper())
        else:
            self._logger = get_logger()
            self._logger.setLevel(log_level.upper())

        # Save parameters; ms set below
        self._show_gui = show_gui
        self._app_name = app_name

        # Set up temp dir for output html files
        self._app_context = AppContext(app_name)

        if show_gui:
            # Enable "toast" notifications
            pn.config.notifications = True
            self._toast = None # for destroy() with new plot or new notification

        # Initialize plot inputs and params
        self._plot_inputs = {'selection': {}}
        self._plot_params = None

        # Initialize plots
        self._plot_init = False
        self._plots_locked = False
        self._plots = []

        # Set data (if ms)
        self._data = None
        self._ms_info = {}
        self._set_ms(ms)
# pylint: enable=too-many-arguments, too-many-positional-arguments

    def summary(self, data_group='base', columns=None):
        ''' Print ProcessingSet summary.
            Args:
                data_group (str): data group to use for summary.
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options: 'name', 'intents', 'shape', 'polarization', 'scan_name', 'spw_name',
                                 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
            Returns: list of unique values when single column is requested, else None
        '''
        if self._data:
            self._data.summary(data_group, columns)
        else:
            self._logger.error("Error: MS path has not been set")

    def data_groups(self):
        ''' Returns set of data groups from all ProcessingSet ms_xds. '''
        if self._data:
            return self._data.data_groups()
        self._logger.error("Error: MS path has not been set")
        return None

    def get_dimension_values(self, dimension):
        ''' Returns sorted list of unique dimension values in ProcessingSet (with previous selection applied, if any).
            Dimension options include 'time', 'baseline' (for visibility data), 'antenna' (for spectrum data), 'antenna1',
                'antenna2', 'frequency', 'polarization'.
        '''
        if self._data:
            return self._data.get_dimension_values(dimension)
        self._logger.error("Error: MS path has not been set")
        return None

    def plot_antennas(self, label_antennas=False):
        ''' Plot antenna positions.
                label_antennas (bool): label positions with antenna names.
        '''
        if self._data:
            self._data.plot_antennas(label_antennas)
        else:
            self._logger.error("Error: MS path has not been set")

    def plot_phase_centers(self, data_group='base', label_fields=False):
        ''' Plot the phase center locations of all fields in the Processing Set and highlight central field.
                data_group (str): data group to use for field and source xds.
                label_fields (bool): label all fields on the plot if True, else label central field only
        '''
        if self._data:
            self._data.plot_phase_centers(data_group, label_fields)
        else:
            self._logger.error("Error: MS path has not been set")

    def clear_plots(self):
        ''' Clear plot list '''
        while self._plots_locked:
            time.sleep(1)
        self._plots.clear()

    def clear_selection(self):
        ''' Clear data selection and restore original ProcessingSet '''
        if self._data:
            self._data.clear_selection()

        self._plot_inputs['selection'] = {}

    def show(self):
        ''' 
        Show interactive Bokeh plots in a browser. Plot tools include pan, zoom, hover, and save.
        '''
        if not self._plots:
            raise RuntimeError("No plots to show.  Run plot() to create plot.")

        # Do not delete plot list until rendered
        self._plots_locked = True

        # Single plot or combine plots into layout using subplots (rows, columns)
        layout_plot = self._layout_plots(self._plot_inputs['subplots'])

        # Render plot as Bokeh Figure or GridPlot
        bokeh_fig = hv.render(layout_plot)

        self._plots_locked = False
        if self._plot_params:
            # Show plot and plot inputs in tabs
            column = pn.Column()
            for param in self._plot_params:
                column.append(pn.pane.Str(param))
            tabs = pn.Tabs(('Plot', bokeh_fig), ('Plot Inputs', column))
            tabs.show(title=self._app_name, threaded=True)
        else:
            show(bokeh_fig)

    def save(self, filename='ms_plot.png', fmt='auto', width=900, height=600):
        '''
        Save plot to file with filename, format, and size.
        If iteration plots were created:
            If subplots is a grid, the layout plot will be saved to a single file.
            If subplots is a single plot, iteration plots will be saved individually,
                with a plot index appended to the filename: {filename}_{index}.{ext}.
        '''
        if not self._plots:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        start_time = time.time()

        name, ext = os.path.splitext(filename)
        fmt = ext[1:] if fmt=='auto' else fmt

        # Combine plots into layout using subplots (rows, columns) if not single plot.
        # Set fixed size for export.
        layout_plot = self._layout_plots(self._plot_inputs['subplots'], (width, height))

        if not isinstance(layout_plot, hv.Layout) and self._plot_inputs['iter_axis']:
            # Save iterated plots individually, with index appended to filename
            plot_idx = 0 if self._plot_inputs['iter_range'] is None else self._plot_inputs['iter_range'][0]
            for plot in self._plots:
                exportname = f"{name}_{plot_idx}{ext}"
                self._save_plot(plot, exportname, fmt)
                plot_idx += 1
        else:
            self._save_plot(layout_plot, filename, fmt)
        self._logger.debug("Save elapsed time: %.2fs.", time.time() - start_time)

    def _layout_plots(self, subplots, fixed_size=None):
        ''' Combine plots in a layout, using fixed size for the layout if given '''
        subplots = (1, 1) if subplots is None else subplots
        num_plots = min(len(self._plots), np.prod(subplots))
        plot_width = fixed_size[0] if fixed_size else None
        plot_height = fixed_size[1] if fixed_size else None

        if num_plots == 1:
            # Single plot, not layout
            plot = self._plots[0]
            if fixed_size:
                plot = plot.opts(responsive=False, width=plot_width, height=plot_height, clone=True)
            return plot

        # Set plots in layout
        layout_plot = None
        for i in range(num_plots):
            plot = self._plots[i]
            if fixed_size:
                plot = plot.opts(responsive=False, width=plot_width, height=plot_height, clone=True)
            layout_plot = plot if layout_plot is None else layout_plot + plot

        # Layout in columns
        return layout_plot.cols(subplots[1])

    def _save_plot(self, plot, filename, fmt):
        ''' Save plot using hvplot, else bokeh '''
        # Remove toolbar unless html
        toolbar = 'right' if fmt=='html' else None
        plot = plot.opts(toolbar=toolbar, clone=True)

        try:
            hvplot.save(plot, filename=filename, fmt=fmt)
        except (Exception, RuntimeError) as exc:
            # Fails if hvplot cannot find web driver or fmt is svg.
            # Render a Bokeh Figure or GridPlot, create webdriver, then use Bokeh to export.
            fig = hv.render(plot)
            if fmt=='html':
                save(fig, filename)
            elif fmt in ['png', 'svg']:
                # Use Chrome web driver
                service = webdriver.ChromeService()
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')

                with webdriver.Chrome(service=service, options=options) as driver:
                    if fmt=='png':
                        export_png(fig, filename=filename, webdriver=driver)
                    elif fmt=='svg':
                        export_svg(fig, filename=filename, webdriver=driver)
            else:
                raise ValueError(f"Invalid fmt or filename extension {fmt} for save()") from exc
        self._logger.info("Saved plot to %s.", filename)

    def _set_ms(self, ms_path):
        ''' Set MsData and update ms info for input ms filepath (MSv2 or zarr), if set.
            Return whether ms changed (false if ms is None). '''
        self._ms_info['ms'] = ms_path
        ms_error = ""
        ms_changed = ms_path and (not self._data or not self._data.is_ms_path(ms_path))

        if ms_changed:
            try:
                # Set new MS data
                self._data = MsData(ms_path, self._logger)
                data_path = self._data.get_path()
                self._ms_info['ms'] = data_path
                root, ext = os.path.splitext(os.path.basename(data_path))
                while ext != '':
                    root, ext = os.path.splitext(root)
                self._ms_info['basename'] = root
                self._ms_info['data_dims'] = self._data.get_data_dimensions()
            except RuntimeError as e:
                ms_error = str(e)
                self._data = None

        if ms_error:
            self._notify(ms_error, 'error', 0)

        return ms_changed

    def _notify(self, message, level, duration=3000):
        ''' Log message. If show_gui, notify user with toast for duration in ms.
            Zero duration must be dismissed. '''
        if self._show_gui:
            pn.state.notifications.position = 'top-center'
            if self._toast:
                self._toast.destroy()

        if level == "info":
            self._logger.info(message)
            if self._show_gui:
                self._toast = pn.state.notifications.info(message, duration=duration)
        elif level == "error":
            self._logger.error(message)
            if self._show_gui:
                self._toast = pn.state.notifications.error(message, duration=duration)
        elif level == "success":
            self._logger.info(message)
            if self._show_gui:
                self._toast = pn.state.notifications.success(message, duration=duration)
        elif level == "warning":
            self._logger.warning(message)
            if self._show_gui:
                self._toast = pn.state.notifications.warning(message, duration=duration)

    def _set_plot_params(self, plot_params):
        ''' Set list of plot parameters as key=value string, for logging or browser display '''
        plot_inputs = plot_params.copy()
        for key in ['self', '__class__', 'data_dims']:
            # Remove keys from using function locals()
            try:
                del plot_inputs[key]
            except KeyError:
                pass
        self._plot_params = sorted([f"{key}={value}" for key, value in plot_inputs.items()])
