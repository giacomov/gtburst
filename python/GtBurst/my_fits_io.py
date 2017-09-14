# If pywcs is installed, use pyfits, otherwise use
# astropy.io.fits

try:
    
    import pywcs
    import pyfits

except:
    
    import astropy.io.fits as pyfits
