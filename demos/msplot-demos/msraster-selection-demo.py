import os
import ssl
import certifi
import urllib
import tarfile
import time

from toolviper.dask.client import local_client

from vidavis.apps import MsRaster

##
## demo measurement set to use
##
ms_path = 'sis14_twhya_selfcal.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/sis14_twhya_selfcal.ms.tar.gz"
##
## where to save plots
##
plot_dir = "demo_plots"

def fetch_ms():
    if not os.path.isdir(ms_path):
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
            tar = tarfile.open(fileobj=tstream, mode="r:gz")
            tar.extractall( )
        except urllib.error.URLError:
            print("Failed to open connection to "+ms_url)
            raise

    if not os.path.isdir(ms_path):
        raise  RuntimeError("Failed to fetch measurement set")


def plot_ms_selection():
    ''' Show MsRaster selection '''
    # Download test ms
    fetch_ms()

    # Create plot directory
    if not os.path.exists(plot_dir):
        os.mkdir(plot_dir)

    # Start toolviper dask client
    client = local_client()

    # Converts ms to zarr, and gets xradio ProcessingSet.
    # logging levels are 'debug', 'info' , 'warning', 'error', 'critical'
    msr = MsRaster(ms_path, log_level='info', show_gui=False)
    select_processing_set(msr)
    select_measurement_set_dimensions(msr)
    msr.unlink_plot_locate()

def select_processing_set(msr):
    # ProcessingSet selection using summary column names and 'data_group_name', and Pandas query
    # Columns: 'name', 'scan_intents', 'shape', 'polarization', 'scan_name', 'spw_name',
    #   'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
    # For selection options, use msr.summary() and msr.data_groups()
    # Select single summary values
    msr.select_ps(field_name='TW Hya_5', scan_name='16', polarization='XX')
    msr.plot()
    msr.show()
    msr.save()

    # Selections are cumulative.
    # Clear selection each time to start with unselected PS.
    msr.clear_selection()

    # Select summary value with dict
    intent_selection = {'scan_intents': 'OBSERVE_TARGET#ON_SOURCE'}
    msr.select_ps(**intent_selection)
    msr.plot()
    msr.show()
    msr.save()

    # Select list of summary values
    msr.clear_selection()
    msr.select_ps(field_name=['J1037-295_3', 'TW Hya_5'], scan_name=['16', '18', '20'], polarization='XX')
    msr.plot()
    msr.show()
    msr.save()

    # Select summary partial match 
    msr.clear_selection()
    msr.select_ps(string_exact_match=False, query=None, scan_intents='CALIBRATE_BANDPASS')
    msr.plot()
    msr.show()
    msr.save()

def select_measurement_set_dimensions(msr):
    # MeasurementSet selection using dimensions names and values, as well as 'data_group_name'.
    # Use get_dimension_values(dim) for selection options for dimensions:
    #   'time', 'baseline' (interferometry), 'antenna' (spectrum), 'antenna1', 'antenna2', 'frequency', 'polarization'
    # See https://docs.xarray.dev/en/stable/generated/xarray.Dataset.sel.html#xarray.Dataset.sel for explanation
    # of parameters (indexers, method, tolerance, drop).  Default method None is exact match.
    # Select numeric values (time and frequency) by value, list, or slice.
    # Select string values (baseline and polarization) by value or list.
    # Note these selections may be combined, but are shown separately for reference.
    select_time(msr)
    select_baseline(msr)
    select_frequency(msr)
    select_polarization(msr)

def select_time(msr):
    ''' Demonstrate methods of selecting time using the string format shown in get_dimension_values('time').
        Since time is a numeric value (although selected using a string), a method such as 'nearest' with a tolerance can be used.
        Select numeric values by value, list, or slice.
    '''
    # Select single time value 
    msr.clear_selection()
    msr.select_ms(time='19-Nov-2012 08:00:04')
    msr.plot(y_axis='frequency') # default is 'time'
    msr.show()
    msr.save()

    # Select single time value nearest 8:45 within 5 second tolerance
    msr.clear_selection()
    msr.select_ms(time='19-Nov-2012 08:45:00', method='nearest', tolerance=5)
    msr.plot(y_axis='frequency') # default is 'time'
    msr.show()
    msr.save()

    # Select list of time values within 30 second tolerance for time axis
    msr.clear_selection()
    msr.select_ms(indexers=None, method='nearest', tolerance=30, drop=False, time=['19-Nov-2012 08:45:00', '19-Nov-2012 08:50:00', '19-Nov-2012 08:58:00', '19-Nov-2012 09:00:00'])
    msr.plot()
    msr.show()
    msr.save()

    # Select slice of time values between 9:00 and 9:12 for time axis; method and tolerance not used for slice.
    msr.clear_selection()
    msr.select_ms(time=slice('19-Nov-2012 09:00:00', '19-Nov-2012 09:12:00'))
    msr.plot()
    msr.show()
    msr.save()

def select_baseline(msr):
    ''' Demonstrate methods of selecting baselines and antennas.
        Use get_dimension_values(dim) with dim = 'baseline', 'antenna1', or 'antenna2' for options.
        There is no syntax for cross-correlation vs auto-correlation.
        Select string values by value or list.
    '''
    # Select single baseline value
    msr.clear_selection()
    msr.select_ms(baseline='DV05_A082 & DV18_A053')
    msr.plot(x_axis='frequency') # default is 'baseline'
    msr.show()
    msr.save()

    # Select list of baselines for baseline axis
    msr.clear_selection()
    msr.select_ms(baseline=['DA44_A068 & DA45_A070', 'DV05_A082 & DV18_A053', 'DV08_A021 & DV16_A069', 'DV20_A020 & DV23_A007'])
    msr.plot()
    msr.show()
    msr.save()

    # Select antenna1 value for baseline axis
    msr.clear_selection()
    msr.select_ms(antenna1='DA44_A068')
    msr.plot()
    msr.show()
    msr.save()

    # Select antenna1 list for baseline axis
    msr.clear_selection()
    msr.select_ms(antenna1=['DA44_A068', 'DA45_A070'])
    msr.plot()
    msr.show()
    msr.save()

    # Select antenna2 value for baseline axis
    msr.clear_selection()
    msr.select_ms(antenna2='DA46_A067')
    msr.plot()
    msr.show()
    msr.save()

    # Select antenna2 list for baseline axis
    msr.clear_selection()
    msr.select_ms(antenna2=['DA46_A067', 'DA48_A046'])
    msr.plot()
    msr.show()
    msr.save()

    # Select baseline, antenna1, antenna2 values for baseline axis
    msr.clear_selection()
    msr.select_ms(baseline='DV05_A082 & DV18_A053', antenna1='DA48_A046', antenna2='DA46_A067')
    msr.plot()
    msr.show()
    msr.save()

def select_frequency(msr):
    ''' Demonstrate methods of selecting frequency. Use get_dimension_values('frequency') options.
        Since frequency is a numeric value, a method such as 'nearest' with a tolerance can be used.
        Select numeric values by value, list, or slice.
    '''
    # Select single frequency value
    msr.clear_selection()
    msr.select_ms(frequency=372640508300.9812)
    msr.plot()
    msr.show()
    msr.save()

    # Select single frequency value nearest 372.534 GHz
    msr.clear_selection()
    msr.select_ms(frequency=3.72534e+11, method='nearest')
    msr.plot()
    msr.show()
    msr.save()

    # Select list of frequency values for frequency axis
    msr.clear_selection()
    msr.select_ms(frequency=[3.72534e+11, 3.72622e+11, 3.72693e+11], method='nearest')
    msr.plot(x_axis='frequency')
    msr.show()
    msr.save()

    # Select nearest frequency value within 100 MHz of 372.6 GHz
    msr.clear_selection()
    msr.select_ms(frequency=3.726e+11, method='nearest', tolerance=1e+8)
    msr.plot()
    msr.show()
    msr.save()

    # Select frequency values between 372.6 - 372.7 GHz; method and tolerance not used for slice
    msr.clear_selection()
    msr.select_ms(frequency=slice(3.726e+11, 3.727e+11))
    msr.plot(x_axis='frequency')
    msr.show()
    msr.save()

def select_polarization(msr):
    ''' Demonstrate methods of selecting polarization. Use get_dimension_values('polarization') options.
        Can select string values by value or list only.
        Select string values by value or list.
    '''
    # Select single polarization value
    msr.clear_selection()
    msr.select_ms(polarization='YY')
    msr.plot()
    msr.show()
    msr.save()

    # Select list of polarization values for x-axis
    msr.clear_selection()
    msr.select_ms(polarization=['XX', 'YY'])
    msr.plot(x_axis='polarization')
    msr.show()
    msr.save()

if __name__ == '__main__':
    plot_ms_selection()
