'''
    Create interactive GUI for ms raster plotting
'''

import panel as pn
from vidavis.plot.ms_plot._ms_plot_selectors import (file_selector, title_selector, style_selector,
    axis_selector, aggregation_selector, iteration_selector, selection_selector, plot_starter)

def create_raster_gui(callbacks, plot_info, empty_plot):
    ''' Use Holoviz Panel to create a dashboard for plot inputs and raster plot display.
        ms (str): path to MS, if set
        plot_info (dict): with keys 'ms', 'data_dims', 'x_axis', 'y_axis'
        empty_plot (hv.Overlay): QuadMesh overlay plot with no data
    '''
    # Accordion of widgets for plot inputs
    selectors = get_plot_input_selectors(callbacks, plot_info)

    # Plot button and spinner while plotting
    init_plot = plot_starter(callbacks['update_plot'])

    # Dynamic map for plot, with callback when inputs change or location needed
    #dmap, points = get_plot_dmap(callbacks, selectors, init_plot)

    return pn.Tabs(
        ('Plot',  pn.Row(                                                  # Tabs[0]
            pn.Column( # Row[0]
                pn.pane.HoloViews(empty_plot), # Column[0] plot
                pn.WidgetBox(),                # Column[1] cursor location
            ),
            pn.Spacer(width=10), # Row[1]
            pn.Column(           # Row[2]
                pn.Spacer(height=25), # Column[0]
                selectors,            # Column[1] selectors
                init_plot,            # Column[2] plot button and spinner
                width_policy='min',
                width=300,
                sizing_mode='stretch_height',
            ),
        )),
        ('Plot Inputs', pn.Column()),                                      # Tabs[1]
        ('Locate Selected Points', pn.Feed(sizing_mode='stretch_height')), # Tabs[2]
        ('Locate Selected Box', pn.Feed(sizing_mode='stretch_height')),    # Tabs[3]
        sizing_mode='stretch_width',
    )

def get_plot_input_selectors(callbacks, plot_info):
    ''' Create accordion of widgets for plot inputs selection '''
    # Select MS
    file_selectors = file_selector(callbacks, plot_info['ms'])

    # Select style - colormaps, colorbar, color limits
    style_selectors = style_selector(callbacks['style'], callbacks['color'])

    # Select x, y, and vis axis
    axis_selectors = axis_selector(plot_info, True, callbacks['axes'])

    # Select from ProcessingSet and MeasurementSet
    selection_selectors = selection_selector(callbacks['select_ps'], callbacks['select_ms'])

    # Generic axis options, updated when ms is set
    data_dims = plot_info['data_dims'] if 'data_dims' in plot_info else None
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
