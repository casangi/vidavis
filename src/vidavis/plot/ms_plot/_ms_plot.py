'''
Base class for ms plots
'''

import os
import logging
import time

from bokeh.io import export_png, export_svg
from bokeh.plotting import save
import hvplot
import holoviews as hv
import numpy as np
import panel as pn
from selenium import webdriver
from toolviper.utils.logger import setup_logger

from vidavis.data.measurement_set._ms_data import MsData
from vidavis.plot.ms_plot._locate_points import cursor_changed, points_changed, box_changed, update_cursor_location, update_points_location, update_box_location
from vidavis.toolbox import AppContext

class MsPlot:

    ''' Base class for MS plots with common functionality '''

# pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(self, ms=None, log_level="info", log_to_file=False, show_gui=False, app_name="MsPlot"):
        if not ms and not show_gui:
            raise RuntimeError("Must provide ms/zarr path if gui not shown.")

        # Set logger: use toolviper logger else casalog else python logger
        self._logger = setup_logger(app_name, log_to_term=True, log_to_file=log_to_file, log_file=app_name.lower(), log_level=log_level.upper())

        # For removing stdout logging when using locate
        self._stdout_handler = None
        for handler in self._logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                self._stdout_handler = handler
                break

        # Save parameters; ms set below
        self._show_gui = show_gui
        self._app_name = app_name

        # Set up temp dir for output html files
        self._app_context = AppContext(app_name)

        # Initialize plot inputs and params
        self._plot_inputs = None # object to manage plot inputs

        # Initialize plots
        self._plot_init = False
        self._plots = []
        self._last_plot = None
        self._plot_params = [] # for plot inputs tab

        if show_gui:
            # Enable "toast" notifications
            pn.config.notifications = True
            self._toast = None # for destroy() with new plot or new notification

            # Initialize gui panel for callbacks
            self._gui_plot_data = None
            self._gui_selection = {}

            # For _update_plot callback: check if inputs changed
            self._last_plot_inputs = None
            self._last_style_inputs = None
            self._last_gui_plot = None # return value

        # For locate callback: check if points changed
        self._plot_axes = None
        self._last_cursor = None
        self._last_points = None
        self._last_box = None
        self._locate_plot_options = {
            'tools': ['hover', 'box_select'],
            'selection_fill_alpha': 0.2,    # dim selected areas of plot
            'nonselection_fill_alpha': 1.0, # do not dim unselected areas of plot
        }

        # Initialize panels for callbacks
        self._gui_panel = None
        self._show_panel = None
        self._plot_data = None

        # Set data (if ms)
        self._ms_data = None
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
        if self._ms_data:
            self._ms_data.summary(data_group, columns)
        else:
            self._logger.error("Error: MS path has not been set")

    def data_groups(self):
        ''' Returns set of data groups from all ProcessingSet ms_xds. '''
        if self._ms_data:
            return self._ms_data.data_groups()
        self._logger.error("Error: MS path has not been set")
        return None

    def get_dimension_values(self, dimension):
        ''' Returns sorted list of unique dimension values in ProcessingSet (with previous selection applied, if any).
            Dimension options include 'time', 'baseline' (for visibility data), 'antenna' (for spectrum data), 'antenna1',
                'antenna2', 'frequency', 'polarization'.
        '''
        if self._ms_data:
            return self._ms_data.get_dimension_values(dimension)
        self._logger.error("Error: MS path has not been set")
        return None

    def plot_antennas(self, label_antennas=False):
        ''' Plot antenna positions.
                label_antennas (bool): label positions with antenna names.
        '''
        if self._ms_data:
            self._ms_data.plot_antennas(label_antennas)
        else:
            self._logger.error("Error: MS path has not been set")

    def plot_phase_centers(self, data_group='base', label_fields=False):
        ''' Plot the phase center locations of all fields in the Processing Set and highlight central field.
                data_group (str): data group to use for field and source xds.
                label_fields (bool): label all fields on the plot if True, else label central field only
        '''
        if self._ms_data:
            self._ms_data.plot_phase_centers(data_group, label_fields)
        else:
            self._logger.error("Error: MS path has not been set")

    def clear_plots(self):
        ''' Clear plot list '''
        self._plots.clear()
        self._plot_params.clear()
        self._plot_axes = None
        if self._gui_panel is not None:
            self._gui_panel[2].clear() # locate points
            self._gui_panel[3].clear() # locate box

    def unlink_plot_locate(self):
        ''' Disconnect streams when plot data is going to be replaced '''
        if self._show_panel and len(self._show_panel.objects) == 4:
            # Remove dmap (streams with callback) from previous plot
            self._show_panel[0][0] = self._last_plot.opts(tools=['hover'])
            # Remove locate widgets
            self._show_panel[0].pop(1) # cursor locate box
            self._show_panel.pop(3)    # box locate tab
            self._show_panel.pop(2)    # points locate tab

    def clear_selection(self):
        ''' Clear data selection and restore original ProcessingSet '''
        if self._ms_data:
            self._ms_data.clear_selection()
        self._plot_inputs.remove_input('selection')

    def show(self):
        ''' 
        Show interactive Bokeh plots in a browser.
        '''
        if not self._plots:
            raise RuntimeError("No plots to show.  Run plot() to create plot.")

        # Single plot or combine plots into layout using subplots (rows, columns)
        subplots = self._plot_inputs.get_input('subplots')
        plot = self._layout_plots(subplots)

        # Add plot inputs column tab
        inputs_column = None
        if self._plot_params:
            inputs_column = pn.Column()
            self._fill_inputs_column(inputs_column)

        # Show plots and plot inputs in tabs
        if self._plot_inputs.is_layout():
            self._show_panel = pn.Tabs(('Plot', plot))
            if inputs_column:
                self._show_panel.append(('Plot Inputs', inputs_column))
        else:
            plot = plot.opts(
                hv.opts.QuadMesh(**self._locate_plot_options),
                hv.opts.Scatter(**self._locate_plot_options)
            )
            # Add DynamicMap for streams for single plot
            dmap = self._get_locate_dmap(self._locate)

            # Create panel layout
            self._show_panel = pn.Tabs(
                ('Plot',
                    pn.Column(
                        plot * dmap,
                        pn.WidgetBox(), # cursor info
                    )
                ),
                sizing_mode='stretch_width',
            )
            if inputs_column:
                self._show_panel.append(('Plot Inputs', inputs_column))
            self._show_panel.append(('Locate Selected Points', pn.Feed(sizing_mode='stretch_height')))
            self._show_panel.append(('Locate Selected Box', pn.Feed(sizing_mode='stretch_height')))

            # return value for locate callback
            self._last_plot = plot

        # Show panel layout
        self._show_panel.show(title=self._app_name, threaded=True)

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
        subplots = self._plot_inputs.get_input('subplots')
        plot = self._layout_plots(subplots, (width, height))

        iter_axis = self._plot_inputs.get_input('iter_axis')
        if not isinstance(plot, hv.Layout) and iter_axis:
            # Save iterated plots individually, with index appended to filename
            iter_range = self._plot_inputs.get_input('iter_range')
            plot_idx = 0 if iter_range is None else iter_range[0]
            for plot in self._plots:
                exportname = f"{name}_{plot_idx}{ext}"
                self._save_plot(plot, exportname, fmt)
                plot_idx += 1
        else:
            self._save_plot(plot, filename, fmt)
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
            Return whether ms changed (false if ms_path is None, not set yet), even if error. '''
        self._ms_info['ms'] = ms_path
        ms_error = ""
        if not ms_path or (self._ms_data and self._ms_data.is_ms_path(ms_path)):
            return False

        try:
            # Set new MS data
            self._ms_data = MsData(ms_path, self._logger)
            data_path = self._ms_data.get_path()
            self._ms_info['ms'] = data_path
            root, ext = os.path.splitext(os.path.basename(data_path))
            while ext != '':
                root, ext = os.path.splitext(root)
            self._ms_info['basename'] = root
            self._ms_info['data_dims'] = self._ms_data.get_data_dimensions()
        except RuntimeError as e:
            ms_error = str(e)
            self._ms_data = None
        if ms_error:
            self._notify(ms_error, 'error', 0)
        return True

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
        if not self._plot_params:
            self._plot_params = plot_inputs
        else:
            for param, value in self._plot_params.items():
                if plot_inputs[param] != value:
                    if isinstance(value, list):
                        # append new value to existing list if not repeat
                        if plot_inputs[param] != value[-1]:
                            value.append(plot_inputs[param])
                    else:
                        # make list to include new value
                        value = [value, plot_inputs[param]]
                    self._plot_params[param] = value

    def _fill_inputs_column(self, inputs_tab_column):
        ''' Format plot inputs and list in Panel column '''
        if self._plot_params:
            inputs_tab_column.clear()
            plot_params = sorted([f"{key}={value}" for key, value in self._plot_params.items()])
            for param in plot_params:
                str_pane = pn.pane.Str(param)
                str_pane.margin = (0, 10)
                inputs_tab_column.append(str_pane)

    def _get_locate_dmap(self, callback):
        ''' Return DynamicMap with streams callback to locate points '''
        points = hv.Points([]).opts(
            size=5,
            fill_color='white'
        )
        dmap = hv.DynamicMap(
            callback,
            streams=[
                hv.streams.PointerXY(),              # cursor location (x, y)
                hv.streams.PointDraw(source=points), # fixed points location (data)
                hv.streams.BoundsXY()                # box location (bounds)
            ]
        )
        return dmap * points

    def _get_plot_axes(self):
        ''' Return x, y, vis axes '''
        if not self._plot_axes:
            x_axis = self._plot_inputs.get_input('x_axis')
            y_axis = self._plot_inputs.get_input('y_axis')
            vis_axis = self._plot_inputs.get_input('vis_axis')
            self._plot_axes = (x_axis, y_axis, vis_axis)
        return self._plot_axes

    def _locate(self, x, y, data, bounds):
        ''' Callback for all show plot streams '''
        self._locate_cursor(x, y, self._plot_data, self._show_panel[0][1])
        self._locate_points(data, self._plot_data, self._show_panel[2])
        self._locate_box(bounds, self._plot_data, self._show_panel[3])
        return self._last_plot

    def _locate_cursor(self, x, y, plot_data, cursor_box):
        ''' Show location from cursor position in cursor locate box '''
        cursor = (x, y)
        if cursor_changed(cursor, self._last_cursor):
            # new cursor position - update cursor location box
            update_cursor_location(cursor, self._get_plot_axes(), plot_data, cursor_box)
            self._last_cursor = cursor

    def _locate_points(self, point_data, plot_data, points_tab):
        ''' Show points locations from point_draw tool '''
        if points_changed(point_data, self._last_points):
            # update selected points location tab
            location_info = update_points_location(point_data, self._get_plot_axes(), plot_data, points_tab)

            # log to file only
            self._logger.removeHandler(self._stdout_handler)
            for info in location_info:
                self._logger.info(info)
            self._logger.addHandler(self._stdout_handler)

            self._last_points = point_data

    def _locate_box(self, box_bounds, plot_data, box_tab):
        ''' Show points locations in box from box_select tool '''
        if box_changed(box_bounds, self._last_box):
            # update selected box location tab
            location_info = update_box_location(box_bounds, self._get_plot_axes(), plot_data, box_tab)

            # log to file only
            self._logger.removeHandler(self._stdout_handler)
            for info in location_info:
                self._logger.info(info)
            self._logger.addHandler(self._stdout_handler)

            self._last_box = box_bounds
