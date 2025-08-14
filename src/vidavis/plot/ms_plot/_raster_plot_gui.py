'''
    Create interactive GUI for ms raster plotting
'''

import holoviews as hv
import panel as pn
from vidavis.plot.ms_plot._ms_plot_selectors import (file_selector, title_selector, style_selector,
    axis_selector, aggregation_selector, iteration_selector, selection_selector, plot_starter)

def create_raster_gui(callbacks, data_dims, x_axis, y_axis):
    ''' Use Holoviz Panel to create a dashboard for plot inputs and raster plot display. '''
    # ------------------
    # PLOT INPUTS COLUMN
    # ------------------
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

    # Plot button and spinner while plotting
    init_plot = plot_starter(callbacks['plot_updating'])

    # ----------------------------------------
    # PLOT WITH CURSOR POSITION AND BOX SELECT
    # ----------------------------------------
    # Connect plot to filename and plot button; add streams for cursor position and selected box
    # 'update_plot' callback must have parameters (ms, do_plot, x, y, data)
    dmap = hv.DynamicMap(
        pn.bind(
            callbacks['update_plot'],
            ms=file_selectors[0][0],
            do_plot=init_plot[0],
        ),
        streams=[
            hv.streams.PointerXY(), # cursor location (x, y)
            hv.streams.BoundsXY()   # box location (bounds)
        ]
    )

    # ----------------------------------------------
    # GUI LAYOUT OF PLOT TABS AND PLOT INPUTS COLUMN
    # ----------------------------------------------
    return pn.Row(
        pn.Tabs(             # Row [0]
            ('Plot',
                pn.Column(                # Tabs [0]
                    dmap,           # [0]
                    pn.WidgetBox(), # [1] cursor location
                )
            ),
            ('Plot Inputs', pn.Column()),         # Tabs [1]
            ('Locate Selected Box', pn.Column()), # Tabs [2]
            sizing_mode='stretch_width',
        ),
        pn.Spacer(width=10), # Row [1]
        pn.Column(  # Row [2]
            pn.Spacer(height=25), # Column [0]
            selectors,            # Column [1]
            init_plot,            # Column [2]
            width_policy='min',
            width=400,
            sizing_mode='stretch_height',
        ),
        sizing_mode='stretch_height',
    )
