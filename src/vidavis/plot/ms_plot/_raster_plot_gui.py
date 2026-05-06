'''
    Create interactive GUI for ms raster plotting
'''

import panel as pn
from vidavis.plot.ms_plot._ms_plot_selectors import (file_selector, title_selector, style_selector,
    axis_selector, aggregation_selector, iteration_selector, selection_selector, plot_starter)

def get_panel_tabs(plot, flag_callback):
    ''' Create tabs for show and gui '''
    # Set up callback for flagging
    flag_button = pn.widgets.Button(
        button_style='outline', # set to 'solid' when points or boxes are drawn
        button_type='primary',  # blue
        description='Flag points or boxes',
        icon='flag',            # icon name loaded from tabler-icons.io
        icon_size='2em',        # 2x parent font
        disabled=True,          # enabled when points or boxes are drawn
        name='Flag Data',
    )
    flag_button.on_click(flag_callback)

    return pn.Tabs(
        ('Plot', pn.Column(                              # Tabs[0]
            plot,   # Column[0] plot
            pn.Row( # Column[1] row under plot
                flag_button,                               # Row[0] flag button
                pn.WidgetBox(sizing_mode='stretch_width'), # Row[1] cursor location
            ),
        )),
        ('Plot Inputs', pn.Column()),                    # Tabs[1]
        ('Locate Points', pn.Feed(height_policy='max')), # Tabs[2]
        ('Locate Box', pn.Feed(height_policy='max')),    # Tabs[3]
        sizing_mode='stretch_width',
    )

def create_raster_gui(callbacks, plot_info, empty_plot):
    ''' Use Holoviz Panel to create a dashboard for plot inputs and raster plot display.
        callbacks (dist): callback functions for widgets
        plot_info (dict): with keys 'ms', 'data_dims', 'x_axis', 'y_axis'
        empty_plot (hv.Overlay): QuadMesh overlay plot with no data
    '''
    # Accordion of widgets for plot inputs
    selectors = get_plot_input_selectors(callbacks, plot_info)

    # Select from ProcessingSet and MeasurementSet
    selection_selectors = selection_selector(callbacks['select_ps'], callbacks['select_ms'])

    # Plot button and spinner while plotting
    init_plot = plot_starter(callbacks['update_plot'])

    # Dynamic map for plot, with callback when inputs change or location needed
    panel_tabs = get_panel_tabs(pn.pane.HoloViews(empty_plot), callbacks['flag'])

    panel_tabs.append(
        ('Plot Settings', pn.Row( # Tabs[4]
            pn.Column(           # Row[0]
                selectors, # Column[0] selectors
                init_plot, # Column[1] plot button and spinner
            ),
            selection_selectors, # Row[1]
        )),
    )
    return panel_tabs

def get_plot_input_selectors(callbacks, plot_info):
    ''' Create accordion of widgets for plot inputs selection '''
    # Select MS
    file_selectors = file_selector(callbacks, plot_info['ms'])

    # Select style - colormaps, colorbar, color limits
    style_selectors = style_selector(callbacks['style'], callbacks['color'])

    # Select x, y, and vis axis
    axis_selectors = axis_selector(plot_info, True, callbacks['axes'])

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
        ("Select file", file_selectors), # [0]
        ("Plot style", style_selectors), # [1]
        ("Plot title", title_input),     # [2]
        ("Plot axes", axis_selectors),   # [3]
        ("Aggregation", agg_selectors),  # [4]
        ("Iteration", iter_selectors),   # [5]
        sizing_mode='stretch_width',
        toggle=True,
    )
    return selectors
