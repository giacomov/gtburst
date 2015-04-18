from GtBurst import aplpy
import matplotlib.pyplot as plt
import pyfits, time, numpy
from GtBurst import dataHandling
from GtBurst import IRFS
import matplotlib.colors as col
import matplotlib.cm as cm

# define individual colors which will be used for classes
cpool                         = [ '#a6cee3','#1f78b4','#b2df8a','#33a02c','#fb9a99','#e31a1c','#fdbf6f','#ff7f00','#cab2d6','#6a3d9a','#ffff99','#b15928']

class InteractiveFt1Display(object):
  def __init__(self,ft1file,skyimage,figure,obj_ra=None,obj_dec=None):
    self.skyimage             = skyimage
    ft1                       = pyfits.open(ft1file)
    self.events               = ft1['EVENTS'].data
    self.empty                = False
    if(len(self.events)==0):
      print("No events in FT1 file %s" %(ft1file))
      self.empty              = True
      #raise RuntimeError("No events in FT1 file %s" %(ft1file))
    pass
    
    self.obj_ra               = obj_ra
    self.obj_dec              = obj_dec
    
    #Read in the different classes of events
    self.trigtime             = dataHandling.getTriggerTime(ft1file)
    time                      = self.events.field("TIME")
    energy                    = self.events.field("ENERGY")
    if(not self.empty):
      self.tmin                 = min(time)-self.trigtime
      self.tmax                 = max(time)-self.trigtime
      self.energyMin            = min(energy)
      self.energyMax            = max(energy)
    else:
      self.tmin               = float(ft1['EVENTS'].header['TSTART'])
      self.tmax               = float(ft1['EVENTS'].header['TSTOP'])
      self.energyMin          = 100
      self.energyMax          = 1e7
    pass
    
    #Get the reprocessing
    self.reprocVer            = str(ft1[0].header['PROC_VER'])
    self.generateColorMap()
    
    #Print a summary
    irfs                      = numpy.array(map(lambda x:IRFS.fromEvclassToIRF(self.reprocVer,x),self.events.field("EVENT_CLASS")))
    print("")
    for irf in IRFS.PROCS[self.reprocVer]:
      try:
        n                     = irfs[irfs==irf].shape[0]
      except:
        n                     = 0
      pass
      print("%-50s %s" %("Class %s only:" % irf,n))

    
    self.pickerID             = None
    self.oldxmin              = -1e9
    self.oldxmax              = 1e9
    self.oldymin              = -1e9
    self.oldymax              = 1e9
    self.user_ra              = None
    self.user_dec             = None
    self.evtext               = None
    
    self.figure               = figure
    self.figure.clear()
    self.displayImage()
    self.initEventDisplay()
    self.displayEvents()
    self.figure.canvas.draw()
    self.connectEvents()
    ft1.close()
  pass
  
  def generateColorMap(self):    
    #Translate from bitmask to color
    
    #Get all IRFS for this reprocessing
    irfs                      = map(lambda x:IRFS.IRFS[x],IRFS.PROCS[self.reprocVer])
    #Order by evclass
    irfs                      = sorted(irfs,key=lambda x:x.evclass)
    self.IRFToColor           = IRFS.CaseInsensitiveDict()
    for i,ir in enumerate(irfs):
      #print("%s (%s) -> %s" %(ir.name,ir.evclass,cpool[i]))
      self.IRFToColor[ir.shortname] = cpool[i]
    pass
  pass
    
  def unbind(self):
    #Clear all bindings in figures
    #print("UNBINDING")
    self.rangerTimer.stop()
    self.timer.stop()
    self.figure.canvas.mpl_disconnect(self.pickerID)
    self.figure.canvas.mpl_disconnect(self.clickerID)
  pass
  
  def displayImage(self):
    self.image               = aplpy.FITSFigure(self.skyimage,convention='calabretta',
                                                figure=self.figure,
                                                subplot=[0.1,0.10,0.40,0.7],
                                                label='sky image')
    
    imageFits                = pyfits.open(self.skyimage)
    img                      = imageFits[0].data
    
    # Apply grayscale mapping of image
    if(not self.empty):
      skm                      = self.image.show_colorscale(cmap='gist_heat',vmin=0.1,
                                                 vmax=max(img.flatten()),
                                                 stretch='log')
    else:
      skm                      = self.image.show_colorscale(cmap='gist_heat',vmin=0,
                                                 vmax=0.1)
    imageFits.close()
    
    # Modify the tick labels for precision and format
    self.image.tick_labels.set_xformat('ddd.dd')
    self.image.tick_labels.set_yformat('ddd.dd')
    
    # Display a grid and tweak the properties
    try:
      self.image.show_grid()
    except:
      #show_grid throw an exception if the grid was already there
      pass
    pass
    
    #Try to plot a cross at the source position
    
    if(self.obj_ra!=None):
      self.image.show_markers([float(self.obj_ra)], [float(self.obj_dec)], edgecolor='cyan', facecolor='cyan',marker='x', s=120, alpha=0.5,linewidth=2)
    
    self.figure.canvas.draw()
  pass
  
  def initEventDisplay(self):
    #This must be called just once!
    self.eventDisplay         = self.figure.add_axes([0.60,0.10,0.35,0.7],label='event display')
  pass
  
  def inRegion(self,ra,dec,xmin,xmax,ymin,ymax):
    #Transform in pixel coordinates then check if ra,dec is contained
    #in the provided rectangular region
    tr                        = self.image._ax1._wcs.wcs_sky2pix
    x,y                       = tr(ra,dec,1)
    if((x>=xmin and x<=xmax) and
       (y>=ymin and y<=ymax)):
       #Contained
       return True
    else:
       return False
    pass
  pass
  
  def mapEventClassesColors(self,classes):
    return map(lambda x:self.IRFToColor[IRFS.fromEvclassToIRF(self.reprocVer,x)],classes)
  pass
  
  def displayEvents(self,xmin=-1,xmax=1e9,ymin=-1,ymax=1e9):
    #Filter data
    idx                       = numpy.array(map(lambda x:self.inRegion(x.field("RA"),x.field("DEC"),xmin,xmax,ymin,ymax),
                                                self.events),'bool')
    
    events                    = self.events[idx]
    
    #Events display
    self.eventDisplay.cla()
    self.eventDisplay.scatter(events.field("TIME")-self.trigtime,
                 events.field("ENERGY"),s=20,c=self.mapEventClassesColors(events.field("EVENT_CLASS")),
                 picker=0,lw=0)
    
    try:
      self.eventDisplay.set_yscale('log')
      self.eventDisplay.set_ylim([self.energyMin*0.8,self.energyMax*1.2])
      self.eventDisplay.set_xlim([self.tmin-0.3*abs(self.tmin),self.tmax+0.3*abs(self.tmax)])  
    except:
      #no events to display, restore linear mode otherwise "figure.canvas.draw()"
      #will fail (!)
      self.eventDisplay.set_yscale('linear')
      pass
    self.eventDisplay.set_ylabel("Energy (MeV)",fontsize='small')
    self.eventDisplay.set_xlabel("Time since trigger (s)",fontsize='small')
    
    #Put the legend on top of the figure
    for k,v in self.IRFToColor.iteritems():
      self.eventDisplay.scatter([],[],s=20,lw=0,label=k,c=v)
    pass
        
    legend                    = self.eventDisplay.legend(scatterpoints=1,
                                            ncol=3,labelspacing=0.01,
                                            columnspacing=0.02,
                                            loc='upper center',
                                            handletextpad=0.1,
                                            bbox_to_anchor=(0.45,1.25),
                                            fancybox=True,)
    ltext                     = legend.get_texts()
    plt.setp(ltext, fontsize='small') 
    legend.get_title().set_fontsize('x-small')
    self.figure.canvas.draw()
    
    #Destroy the callback with previous data, and create a new one with the new data
    if(self.pickerID!=None):
      self.figure.canvas.mpl_disconnect(self.pickerID)
    pass
    self.pickerID             = self.figure.canvas.mpl_connect('pick_event',
                                                                lambda x:self.on_events_plot_click(x,events))
  pass
  
  def connectEvents(self):
    self.clickerID            = self.figure.canvas.mpl_connect('button_press_event',self.on_click)
    self.timer                = self.figure.canvas.new_timer(interval=200)
    self.timer.add_callback(self.keep_synch, self.image._ax1)
    self.rangerTimer          = self.figure.canvas.new_timer(interval=100)
    self.rangerTimer.add_callback(lambda x:self.clearRanger(x,self.rangerTimer),self.figure)
    self.timer.start()
    self.rangerTimer.start()
  pass
  
  def waitClick(self):
    #Put the window in waiting mode, waiting for a click on the sky image
    self.locking              = True
    self.figure.canvas.start_event_loop(0)
  pass
  
  def on_click(self,event):
    if(event.inaxes==None):
      #Click outside any plot, do nothing
      return
    pass
    
    if(event.inaxes.get_label()!='event display'):
      #This is a click on the sky image, get the corresponding ra,dec
      ax                      = self.image._ax1
      if(ax.get_navigate_mode()==None):
        ra,dec                = ax._wcs.wcs_pix2sky(event.xdata,event.ydata,1)
        self.user_ra          = ra[0]
        self.user_dec         = dec[0]
        self.figure.canvas.stop_event_loop()
      else:
        #We are in zoom mode, do nothing
        return
    else:
      #the click was not on the sky image. Do nothing
      return
    pass
  pass
  
  def clearRanger(self,event,rangerTimer):
    #Verify if the figure has been cleared. If so, remove all bindings
    if(len(self.figure.get_axes())==0):
      rangerTimer.stop()
      self.unbind()
    pass
  pass
  
  def keep_synch(self,event=None):
    ax                     = self.image._ax1
    
    nx                     = ax.get_xlim()
    ny                     = ax.get_ylim()
    ras, decs              = ax._wcs.wcs_pix2sky(nx,ny,1)
    xmin                   = nx[0]
    xmax                   = nx[1]
    ymin                   = ny[0]
    ymax                   = ny[1]
    if(xmin!=self.oldxmin or ymin!=self.oldymin or
       xmax!=self.oldxmax or ymax!=self.oldymax):
      self.displayEvents(xmin,xmax,ymin,ymax)
      self.oldxmin           = xmin
      self.oldxmax           = xmax
      self.oldymin           = ymin
      self.oldymax           = ymax
      #refresh, avoiding an infinite loop
      self.figure.canvas.draw()
    else:
      #Not changed
      return
  pass
  
  def on_events_plot_click(self,event,events):
    ind                 = event.ind[0]
    
    try:
      ras             = events.field("RA")[ind]
      decs            = events.field("DEC")[ind]
      event_id        = events.field("EVENT_ID")[ind]
      run_id          = events.field("RUN_ID")[ind]
      theta           = events.field("THETA")[ind]
      zenith          = events.field("ZENITH_ANGLE")[ind]
      time            = events.field("TIME")[ind]
      energy          = events.field("ENERGY")[ind]
    except:
      print("Could not get Ra,Dec of your event. Please retry...")
      pass
    
    #Get the width and height (in deg) of the image display
    ax                     = self.image._ax1
    nx                     = ax.get_xlim()
    ny                     = ax.get_ylim()
    rass, decss            = ax._wcs.wcs_pix2sky(nx,ny,1)
    img_width              = min(abs(rass[0]-rass[1]),abs(decss[0]-decss[1]))
    radius_length          = 0.3
    
    self.image.show_circles([ras],[decs],[radius_length],
                           facecolor='white',layer="circle",alpha=0.8)
    if(self.evtext!=None):
      try:
        self.evtext.remove()
      except:
        #if the user zoom between one and another, this will be emptied already
        pass
    self.evtext            = self.eventDisplay.text(time-self.trigtime,energy,
                                                    'run = %s\nid = %s\ntheta = %3.1f\nzenith = %3.1f' % (run_id,event_id,theta,zenith),
                                                    color='green',verticalalignment='top',size='small',fontweight='bold')

    self.figure.canvas.draw()
  pass
pass
