import os
import ssl
import certifi
import urllib
import tarfile

from casagui.apps import plotms

##
## demo measurement set to use
##
ms_path = 'sis14_twhya_calibrated_flagged.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casagui/sis14_twhya_calibrated_flagged.ms.tar.gz"

##
## output image file name
##
plotfile = 'test.png'

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

# Defaults: Amp vs. Time, showplot=True
plotms(vis=ms_path, xaxis='time', yaxis='amp', showplot=True, plotfile='plotms_test.png')

