#!/usr/bin/env python

import matplotlib as mpl
mpl.use('Agg')
from GtBurst import aplpy
import matplotlib.pyplot as plt
import sys
import pyfits
    
def fitsToPNG(fitsfile,pngfile,vmin=None,vmax=None,**kwargs):
    #Display the TS map    
    #figure                      = plt.figure()
    tsfig                       = aplpy.FITSFigure(fitsfile,convention='calabretta')
    tsfig.set_tick_labels_font(size='small')
    tsfig.set_axis_labels_font(size='small')
    if(vmin!=None and vmax!=None):
      tsfig.show_colorscale(cmap='gist_heat',aspect='auto',vmin=float(vmin),vmax=float(vmax))
    else:
      #Get maximum of image
      f                         = pyfits.open(fitsfile)
      maximum                   = f[0].data.max()
      f.close()
      tsfig.show_colorscale(cmap='gist_heat',aspect='auto',vmin=0,vmax=float(maximum))
    # Modify the tick labels for precision and format
    tsfig.tick_labels.set_xformat('ddd.dd')
    tsfig.tick_labels.set_yformat('ddd.dd')
    
    # Display a grid and tweak the properties
    tsfig.show_grid()
    tsfig.add_colorbar()
    
    if('sources' in kwargs.keys()):
      sources                 = kwargs['sources']
      for src in sources:
        tsfig.add_label(float(src[1]),float(src[2]), "%s" % src[0],
                        relative=False,weight='bold',color='green', size='x-small',
                        verticalalignment='top', horizontalalignment='left')
        tsfig.show_markers([float(src[1])],[float(src[2])],edgecolor='green',marker='x')
      pass
    if('ra' in kwargs.keys()):
      ra                      = float(kwargs['ra'])
      dec                     = float(kwargs['dec'])
      tsfig.show_markers([ra],[dec],edgecolor='cyan',facecolor='cyan',marker='x',s=120,alpha=0.5,linewidth=3)
    pass
    
    #figure.canvas.draw()
    tsfig.save(pngfile)
pass

def fitsToPNGembedded(fitsfile,pngfile='__png',vmin=None,vmax=None,**kwargs):
    fitsToPNG(fitsfile,pngfile,vmin,vmax,**kwargs)
    data_uri                  = open(pngfile, 'rb').read().encode('base64').replace('\n', '')
    #img_tag                   = '<img src="data:image/png;base64,{0}">'.format(data_uri)
    return data_uri
    
pass

if __name__=='__main__':
  #Get all key=value pairs as a dictionary
  fitsfile                    = sys.argv[1]
  pngfile                     = sys.argv[2]
  if(len(sys.argv)==5):
    ra                        = sys.argv[3]
    dec                       = sys.argv[4]
  else:
    ra                        = None
    dec                       = None
  pass
  
  fitsToPNG(fitsfile,pngfile,ra=ra,dec=dec)
