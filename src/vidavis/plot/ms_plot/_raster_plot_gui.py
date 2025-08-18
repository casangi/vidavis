'''
    Create interactive GUI for ms raster plotting
'''

import holoviews as hv
import panel as pn
from vidavis.plot.ms_plot._ms_plot_selectors import (file_selector, title_selector, style_selector,
    axis_selector, aggregation_selector, iteration_selector, selection_selector, plot_starter)

def create_raster_gui(callbacks, data_dims, x_axis, y_axis):
    ''' Use Holoviz Panel to create a dashboard for plot inputs and raster plot display. '''
    # Accordion of widgets for plot inputs
    selectors = get_plot_input_selectors(callbacks, data_dims, x_axis, y_axis)

    # Plot button and spinner while plotting
    init_plot = plot_starter(callbacks['plot_updating'])

    # Dynamic map for plot, with callback when inputs change or location needed
    dmap, points = get_plot_dmap(callbacks, selectors, init_plot)

    return pn.Row(
        pn.Tabs(             # Row [0]
            ('Plot',                                 # Tabs[0]
                pn.Column(
                    dmap * points,  # [0] plot with hv.Points overlay for point_draw
                    pn.WidgetBox(), # [1] cursor location
                )
            ),
            ('Plot Inputs', pn.Column()),            # Tabs[1]
            ('Locate Selected Points', pn.Column()), # Tabs[2]
            ('Locate Selected Box', pn.Column()),    # Tabs[3]
            sizing_mode='stretch_width',
        ),
        pn.Spacer(width=10), # Row [1]
        pn.Column(  # Row [2]
            pn.Spacer(height=25), # Column[0]
            selectors,            # Column[1]
            init_plot,            # Column[2]
            width_policy='min',
            width=400,
            sizing_mode='stretch_height',
        ),
        sizing_mode='stretch_height',
    )

def get_plot_input_selectors(callbacks, data_dims, x_axis, y_axis):
    ''' Create accordion of widgets for plot inputs selection '''
    # Select MS
    file_selectors = file_selector('Path to MeasurementSet (ms or zarr) for plot', '~' , callbacks['filename'])

    # Select style - colormaps, colorbar, color limits
    style_selectors = style_selector(callbacks['style'], callbacks['color'])

    # Select x, y, and vis axis
    axis_selectors = axis_selector(x_axis, y_axis, data_dims, True, callbacks['axes'])

    # Select from ProcessingSet and MeasurementSet
    selection_selectors = selection_selector(callbacks['select_ps'], callbacks['select_ms'])

    # Generic axis options, updated when ms is set
    axis_options = data_dims if data_dims else []

    # Select aggregator and axes to aggregate
    agg_selectors = aggregation_selector(axis_options, callbacks['aggregation'])

    # Select iter_axis and iter value or range
    iter_selectors = iteration_selector(axis_options, callbacks['iter_values'], callbacks['iteration'])

    # Set title
    title_input = title_selector(callbacks['title'])

    # Put user input widgets in accordion with only one card active at a time (toggle)
    selectors = pn.Accordion(
        ("Select file", file_selectors),         # [0]
        ("Plot style", style_selectors),         # [1]
        ("Data Selection", selection_selectors), # [2]
        ("Plot axes", axis_selectors),           # [3]
        ("Aggregation", agg_selectors),          # [4]
        ("Iteration", iter_selectors),           # [5]
        ("Plot title", title_input),             # [6]
    )
    selectors.toggle = True
    return selectors

def get_plot_dmap(callbacks, selectors, init_plot):
    ''' Dynamic map for updating plot from callback function '''
    # Connect plot to filename and plot button; add streams for cursor position, drawn points, and selected box
    # 'update_plot' callback must have parameters (ms, do_plot, x, y, data, bounds)
    points = hv.Points([]).opts(
        size=5,
        fill_color='white'
    )
    dmap = hv.DynamicMap(
        pn.bind(
            callbacks['update_plot'],
            ms=selectors[0][0][0],
            do_plot=init_plot[0],
        ),
        streams=[
            hv.streams.PointerXY(),              # cursor location (x, y)
            hv.streams.PointDraw(source=points), # fixed cursor location (data)
            hv.streams.BoundsXY()                # box location (bounds)
        ]
    )
    return dmap, points
