import pyfits
import pywcs
import numpy
from pyLikelihood import SkyDir
from GtBurst.angularDistance import getAngularDistance
from GtBurst.angularDistance import getBoundingCoordinates

class DimensionError(ValueError):
    pass

def cutout(filename, ra_or_l, dec_or_b, coordsys, radius, outfile, clobber=True):
    """
    Inputs:
        file  - .fits filename or pyfits HDUList. If HDU is 3d (data-cube), the 3rd dimension
                (the one which is not a sky coordinate) will be kept untouched. Dimensions > 3
                are not supported
        ra_or_l,dec_or_b - Longitude and latitude of the center of the new image. The longitude
                           coordinate (R.A. or L) goes from 0 to 360, while the latitude coordinate
                           goes from -90 to 90.
        coordsys - Coordinate system for the center of the new image ('galactic' or 'equatorial')
        radius - radius of the region of interest (deg)
        outfile - output file
        clobber - overwrite the file if existing? (True or False)
    """
    
    if coordsys not in ['equatorial','galactic']:
      raise ValueError("Unknown coordinate system '%s'" %(coordsys))
    
    if(ra_or_l < 0 or ra_or_l > 360):
      raise RuntimeError("The longitude coordinate must be 0 < longitude < 360")
    
    if(dec_or_b < -90 or dec_or_b > 90):
      raise RuntimeError("The latitude coordinate must be -90 < latitude < 90")
        
    with pyfits.open(filename) as f:
      
      if(f[0].data.ndim==3):
        isCube                     = True
      elif(f[0].data.ndim==2):
        isCube                     = False
      else:
        raise RuntimeError("Do not know how to handle a cube with %s dimensions" %(f[0].data.shape[0]))
      pass
      
      head                         = f[0].header.copy()
      
      cd1                          = head.get('CDELT1') if head.get('CDELT1') else head.get('CD1_1')
      cd2                          = head.get('CDELT2') if head.get('CDELT2') else head.get('CD2_2')
      if cd1 is None or cd2 is None:
          raise Exception("Missing CD or CDELT keywords in header")
      
      wcs                         = pywcs.WCS(head)
      
      #Ensure that the center is expressed in the same coordinate system as the original
      #image
      if coordsys=='equatorial' and wcs.wcs.lngtyp=='GLON':
      
            #Convert RA,Dec in Galactic coordinates
            sdir                        = SkyDir(ra_or_l,dec_or_b,SkyDir.EQUATORIAL)
            xc,yc                       = (sdir.l(),sdir.b())
      
      elif coordsys=='galactic' and wcs.wcs.lngtyp=='RA':
            
            #Convert L,B in Equatorial coordinates
            sdir                        = SkyDir(ra_or_l,dec_or_b,SkyDir.EQUATORIAL)
            xc,yc                       = (sdir.ra(),sdir.dec())

      else:
      
           #Image and input are in the same system already
           xc,yc                        = (ra_or_l,dec_or_b)
      
      pass
      
      #Find the pixel corresponding to the center
      if(isCube):
        #Data cube
        coord                      = numpy.array([[xc],[yc],[1]]).T
        xx,yy,z                    = wcs.wcs_sky2pix(coord,0)[0]
        shapez,shapey,shapex       = f[0].data.shape
        
        #Compute the sky coordinates of all pixels 
        #(will use them later for the angular distance)
        
        #The code below is much faster, but does the same thing as this
        #one here:
        
        #coord                        = numpy.zeros((shapex*shapey,3))
        #h                            = 0
        #for i in range(shapex):
        #  for j in range(shapey):
        #    coord[h]                 = [i+1,j+1,1]
        #    h                       += 1
        
        coord                        = numpy.ones((shapex*shapey,3))
        firstColBase                 = numpy.arange(shapex)+1
        firstColumn                  = numpy.repeat(firstColBase,shapey)
        secondColumn                 = numpy.array(range(shapey)*shapex)+1
        coord[:,0]                   = firstColumn
        coord[:,1]                   = secondColumn
                        
        #Note that pix2sky always return the latitude from 0 to 360 deg
        res                          = wcs.wcs_pix2sky(coord,1)
        ras                          = res[:,0]
        decs                         = res[:,1]
        
      else:
        #Normal image
        coord                       = numpy.array([[xc],[yc]]).T
        xx,yy                       = wcs.wcs_sky2pix(coord,0)[0]
        shapey,shapex               = f[0].data.shape
        
        #Compute the sky coordinates of all pixels 
        #(will use them later for the angular distance)
        coord                        = numpy.ones((shapex*shapey,2))
        firstColBase                 = numpy.arange(shapex)+1
        firstColumn                  = numpy.repeat(firstColBase,shapey)
        secondColumn                 = numpy.array(range(shapey)*shapex)+1
        coord[:,0]                   = firstColumn
        coord[:,1]                   = secondColumn
                        
        #Note that pix2sky always return the latitude from 0 to 360 deg
        res                          = wcs.wcs_pix2sky(coord,1)
        ras                          = res[:,0]
        decs                         = res[:,1]
      pass
        
      print("Center is (%s,%s) pixel, (%s,%s) sky" %(xx,yy,xc,yc))
      
      #Cannot deal with fractional pixel
      if(xx - int(xx) >= 1e-4):
        print("Approximating the X pixel: %s -> %s" %(xx,int(xx)))
        xx                          = int(xx)
      if(yy - int(yy) >= 1e-4):
        print("Approximating the Y pixel: %s -> %s" %(yy,int(yy)))
        yy                          = int(yy)
      pass
      
      #Now select the pixels to keep
      #Pre-select according to a bounding box
      #(huge gain of speed in the computation of distances)
      ra_min_,ra_max_,dec_min_,dec_max_,pole = getBoundingCoordinates(xc,yc,radius)
      
      if(pole):
        #Nothing we can really do, except masking out (zeroing) all the useless parts
        print("\nOne of the poles is within the region. Cannot cut the image. I will zero-out useless parts")
        img                           = f[0].data
        
        #Find the pixel corresponding to (xc,yc-radius)
        coord                         = numpy.array([[xc],[yc-radius],[1]]).T
        res                           = wcs.wcs_sky2pix(coord,0)[0]
        mask_ymax                     = res[1]
        
        #Now find the pixel corresponding to (xc,yc+radius)
        coord                         = numpy.array([[xc],[yc+radius-180.0],[1]]).T
        res                           = wcs.wcs_sky2pix(coord,0)[0]
        mask_ymin                     = res[1]
                
        img[:,mask_ymin:mask_ymax,:]  = img[:,mask_ymin:mask_ymax,:]*0.0
        
      else:
        if(ra_min_ > ra_max_):
          #Circular inversion (ex: ra_min_ = 340.0 and ra_max_ = 20.0)
          idx                         = (ra_min_ <= ras) | (ras <= ra_max_)
        else:
          idx                         = (ra_min_ <= ras) & (ras <= ra_max_)
        pass
        
        if(dec_min_ > dec_max_):
          #Circular inversion (ex: ra_min_ = 340.0 and ra_max_ = 20.0)
          idx                         = ((dec_min_ <= decs) | (decs <= dec_max_)) & idx
        else:
          idx                         = ((dec_min_ <= decs) & (decs <= dec_max_)) & idx
        pass
              
        ras                           = ras[idx]
        decs                          = decs[idx]
        
        #Compute all angular distances of remaining pixels
        distances                     = getAngularDistance(xc,yc,ras,decs)
        
        #Select all pixels within the provided radius
        idx                           = (distances <= radius)
        selected_ras                  = ras[idx]
        selected_decs                 = decs[idx]
                
        #Now transform back into pixels values
        if(isCube):
          
          coord                      = numpy.vstack([selected_ras,selected_decs,[1]*selected_ras.shape[0]]).T
                    
        else:
          
          coord                      = numpy.vstack([selected_ras,selected_decs]).T
        
        pass
        
        res                        = wcs.wcs_sky2pix(coord,0)
        
        #Now check if the range of x is not continuous (i.e., we are
        #wrapping around the borders)
        uniquex                    = numpy.unique(res[:,0])
        deltas                     = uniquex[1:]-uniquex[:-1]
        if(deltas.max()>1):
          #We are wrapping around the borders
          # |-------x1             x2-------|
          #We want to express x2 as a negative index starting
          #from the right border, and set it as xmin.
          #Then we set x1 as xmax.
          #This way the .take method below will start accumulating
          #the image from x2 to the right border |, then from the left
          #border | to x1, in this order
          #Find x2
          x2id                     = deltas.argmax()+1
          x2                       = int(uniquex[x2id])
          x1                       = int(uniquex[x2id-1])
          xmin                     = x2-shapex
          xmax                     = x1
          
          ymin,ymax                = (int(res[:,1].min()),int(res[:,1].max()))
          
        else:          
        
          xmin,xmax,ymin,ymax      = (int(res[:,0].min()),int(res[:,0].max()),int(res[:,1].min()),int(res[:,1].max()))
        
        pass        
        
        print("X range -> %s - %s" %(xmin,xmax))
        print("Y range -> %s - %s" %(ymin,ymax))
        print("Input image shape is ([z],y,x) = %s" %(str(f[0].shape)))
        
        #Using the mode='wrap' option we wrap around the edges of the image,
        #if ymin is negative
        if(isCube):
          
          img                        = f[0].data.take(range(ymin,ymax),mode='wrap', axis=1).take(range(xmin,xmax),mode='wrap',axis=2)
        
        else:
          
          img                        = f[0].data.take(range(ymin,ymax),mode='wrap', axis=0).take(range(xmin,xmax),mode='wrap',axis=1)
        
        pass
        
        #Put the origin of the projection in the right place
        #in the new image
        head['CRPIX1']               -= xmin
        head['CRPIX2']               -= ymin
        
        #Update the length of the axis
        head['NAXIS1']               = int(xmax-xmin)
        head['NAXIS2']               = int(ymax-ymin)
    
        if head.get('NAXIS1') == 0 or head.get('NAXIS2') == 0:
            raise ValueError("Map has a 0 dimension: %i,%i." % (head.get('NAXIS1'),head.get('NAXIS2')))
      pass
      
      newfile = pyfits.PrimaryHDU(data=img,header=head)
      
      newfile.writeto(outfile,clobber=clobber)
      #Append the other extension, if present
      for i in range(1,len(f)):
        pyfits.append(outfile,f[i].data,header=f[i].header)
    
    pass #Close the input file
    
    #Now re-open the output file and fix the wcs 
    #by moving the reference pixel to the 1,1 pixel
    #This guarantee that no pixel will be at a distance larger than 180 deg
    #from the reference pixel, which would confuse downstream software
    if(not pole):
      with pyfits.open(outfile,'update') as outf:
        head                         = outf[0].header
        #Get the 
        wcs                          = pywcs.WCS(head)
        
        #Find the sky coordinates of the 1,1 pixel
        if(isCube):
          #Data cube
          coord                       = numpy.array([[1],[1],[1]]).T
          sx,sy,z                     = wcs.wcs_pix2sky(coord,1)[0]
        else:
          #Normal image
          coord                       = numpy.array([[1],[1]]).T
          sx,sy                       = wcs.wcs_pix2sky(coord,1)[0]
        pass
        
        head['CRPIX1']                = 1
        head['CRVAL1']                = sx
      
      
    pass


