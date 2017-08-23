# This module provides a WCS class which has the same interface as
# the pywcs WCS class. If using the astropy.wcs.WCS implementation,
# that class is monkey patched to be a drop-in replacement for the pywcs
# one

try:
    
    import astropy.io.fits as pyfits
    import astropy.wcs as pywcs
    
    # Monkeypatch the WCS object so that it behaves like the
    # pywcs object
    pywcs.WCS.wcs_pix2sky = pywcs.WCS.all_pix2world
    pywcs.WCS.wcs_sky2pix = pywcs.WCS.all_world2pix
    
except ImportError:
    
    import pyfits
    import pywcs
