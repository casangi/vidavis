########################################################################
#
# Copyright (C) 2022,2024
# Associated Universities, Inc. Washington DC, USA.
#
# This script is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning AIPS++ should be adressed as follows:
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
# pylint: disable=wrong-import-position
'''End user applications supplied by ``casagui``.'''
import sys
from ..utils import copydoc, ImportProtectedModule
from ..bokeh.state import initialize_session
initialize_session()

sys.modules[__name__].__class__ = ImportProtectedModule( __name__, { 'plotants': '._plotants',
                                                                     'plotbandpass': '._plotbandpass',
                                                                     'CreateMask': '._createmask',
                                                                     'CreateRegion': '._createregion',
                                                                     'InteractiveClean': '._interactiveclean',
                                                                     'iclean': '..private.casatasks.iclean',
                                                                     'createmask': '..private.casatasks.createmask',
                                                                     'createregion': '..private.casatasks.createregion',
                                                                     'MsRaster': '._ms_raster',
                                                                   } )
