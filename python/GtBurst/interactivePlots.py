import math
import numpy as np
import pyfits
import matplotlib.pyplot as plt
plt.ion()
from Tkinter import *
import time
import threading
from GtBurst import dataHandling

#This function goes from names like NAI_00 to names like n0
def transformGBMdetname(name):
  translations                = {'NAI_00': 'n0',
                                 'NAI_01': 'n1',
                                 'NAI_02': 'n2',
                                 'NAI_03': 'n3',
                                 'NAI_04': 'n4',
                                 'NAI_05': 'n5',
                                 'NAI_06': 'n6',
                                 'NAI_07': 'n7',
                                 'NAI_08': 'n8',
                                 'NAI_09': 'n9',
                                 'NAI_10': 'na',
                                 'NAI_11': 'nb',
                                 'BGO_00': 'b0',
                                 'BGO_01': 'b1'}
  if(name in translations.keys()):
    return translations[name]
  else:
    return name                                 
pass

def getInteractiveFigureFromCSPEC(cspecfile,**kwargs):
  trigTime                    = dataHandling.getTriggerTime(cspecfile)
  f                           = pyfits.open(cspecfile)  
  if('DETNAM' in f['SPECTRUM'].header.keys()):
    detector                  = transformGBMdetname(f['SPECTRUM'].header['DETNAM'])
  elif('LLECUT' in f['SPECTRUM'].header.keys()):
    detector                  = "LAT"
  elif('TELESCOP' in f['SPECTRUM'].keys()):
    detector                  = f['SPECTRUM'].header['TELESCOP']
  else:    
    detector                  = 'Unknown'
  pass
  s                           = f['SPECTRUM']
  
  d                           = s.data[(s.data.field('QUALITY')==0)]
  #Avoid overflow and underflow channels
  counts                      = d.field('COUNTS')[:,3:126]
  met                         = d.field('TIME')-trigTime
  exposure                    = d.field('EXPOSURE')
  N                           = len(met)
  LC                          = np.zeros(N)
  
  for i in range(N): 
    LC[i]=counts[i].sum()
  
  mask                        = (exposure > 0)
  LC[mask]                   /= exposure[mask]
  kwargs['xlabel']            = "Time since trigger"
  kwargs['ylabel']            = "Counts/s"
  kwargs['xoffset']           = trigTime
  kwargs['title']             = detector
  interactiveFigure           = InteractiveFigure(met,LC,**kwargs)
  f.close()
  
  return interactiveFigure
pass

class InteractiveFigure(object):
  def __init__(self,x,y,**kwargs):
    
    self.xlabel               = ''
    self.ylabel               = ''
    self.title                = ''
    self.selectBackground     = True
    self.selectSource         = True
    self.xoffset              = 0
    self.figure               = None  
    for key in kwargs.keys():
      if   key.lower()=="xlabel":                self.xlabel               = kwargs[key]
      elif key.lower()=="ylabel":                self.ylabel               = kwargs[key]
      elif key.lower()=="title" :                self.title                = kwargs[key]
      elif key.lower()=="selectbackground":      self.selectBackground     = bool(kwargs[key])
      elif key.lower()=="selectsource":          self.selectSource         = bool(kwargs[key])
      elif key.lower()=="xoffset":               self.xoffset              = kwargs[key]
      elif key.lower()=="figure" :               self.figure               = kwargs[key]
    self.x                    = x
    self.y                    = y
    
    if(self.figure==None):  
      self.figure               = plt.figure()
      self.figure.canvas.mpl_connect('close_event', self.closing)
      self.figureIsMine         = True
    else:
      #Clean the figure
      self.figure.clear()
      self.figureIsMine         = False
    pass
      
    self.subfigure            = self.figure.add_subplot(1,1,1,xlabel=self.xlabel,ylabel=self.ylabel)
    self.subfigure.text(0.05, 0.9,'%s' %(self.title), 
                        horizontalalignment='left', 
                        verticalalignment='top',
                        transform = self.subfigure.transAxes)
    self.clearButton          = self.figure.text(0.9, 0.15,'Clear',
                                                 horizontalalignment='left', 
                                                 verticalalignment='top',
                                                 backgroundcolor='red',
                                                 color='white',weight='bold',
                                                 picker=20)
    self.doneButton           = self.figure.text(0.9, 0.05,'Done',
                                                 horizontalalignment='left', 
                                                 verticalalignment='bottom',
                                                 backgroundcolor='green',
                                                 color='white',weight='bold',
                                                 picker=20)
    
    self.backgroundBounds     = []
    self.sourceBounds         = []
    
    self.sourceFillers        = []
    self.backgroundFillers    = []
    
    self.locking              = False
    
    self.curXdata             = 'safetynet'
    self.curYdata             = 'safetynet'
    
  pass
  
  def plot(self):
    self.subfigure.step(self.x,self.y,where='post')
  pass
  
  def bind(self):
    self.cids                 = []
    self.cids.append(self.figure.canvas.mpl_connect('button_press_event', self.clickPress))
    self.cids.append(self.figure.canvas.mpl_connect('button_release_event', self.clickRelease))
    self.cids.append(self.figure.canvas.mpl_connect('motion_notify_event',self.drawLineUnderCursor))
    self.cids.append(self.figure.canvas.mpl_connect('pick_event', self.onPick))    
  
  def unbind(self):
    for cid in self.cids:
      self.figure.canvas.mpl_disconnect(cid)
  pass    
  
  def activate(self):
    self.plot()
    self.figure.canvas.draw()
    self.transitoryLines      = []
    self.lines                = []
    self.bind()
  pass
  
  def onPick(self,event):
    #If the user clicked on one of the texts, do the corresponding
    #action
    if(event.mouseevent.button!=1 or not self.isNormalMode(event)):
      #Do nothing
      return
    pass
    if(event.artist==self.clearButton):
      #clear
      #print 'RESET SELECTION'
      NB                    = len(self.backgroundBounds)
      
      for x in range(NB): 
        self.backgroundBounds.pop()
      
      NS                    = len(self.sourceBounds)
      for x in range(NS): 
        self.sourceBounds.pop()
      
      NOB                   = len(self.backgroundFillers)
      for i in range(NOB): 
        self.backgroundFillers[i].remove()        
      for i in range(NOB): 
        self.backgroundFillers.pop()
      
      NOS                   = len(self.sourceFillers)
      for i in range(NOS): 
        self.sourceFillers[i].remove()
      for i in range(NOS): 
        self.sourceFillers.pop()
      #Suspend the binding for a second
      self.unbind()
      if(len(self.subfigure.lines)!=0):
        self.delLines(self.lines)
        self.delLines(self.transitoryLines)
      pass
      self.bind()
      self.figure.canvas.draw()
    elif(event.artist==self.doneButton):
      #exit
      self.unbind()
      self.cleanClose()
  pass
  
  def delLines(self,lines):
    for ll in lines:
          self.subfigure.lines.remove(ll)
    for i in range(len(lines)):
          lines.pop()
    self.figure.canvas.draw()           
  
  def isNormalMode(self,event):    
    if(len(self.figure.axes)>0):
      ax                        = self.figure.axes[0]
      navmode                   = ax.get_navigate_mode()
      if(navmode==None):
        return True
      else:
        return False
    else:
      #This can happen when I'm closing the window
      return False     
  
  def drawLineUnderCursor(self,event):
    #I want to draw the line only when I am in normal mode
    #(no zoom/pan)
    
    if(event.xdata==None or event.ydata==None or not self.isNormalMode(event)):
      #Mouse outside figure or mode not normal
      self.delLines(self.transitoryLines)
      return
    pass
    self.delLines(self.transitoryLines)
    self.transitoryLines.append(self.drawVerticalLine(event.xdata))
  pass
  
  def drawVerticalLine(self,x):
    line                      = self.subfigure.axvline(x,linestyle="--")
    self.figure.canvas.draw()
    return line
  pass
  
  def drawIntervals(self,fillers,bounds,facecolor):
    n                         = len(bounds)
    if n<2 or n%2!=0: 
      #nothing to do!
      return None
    pass
    self.delLines(self.lines)  
    #This is to avoid a change in the y scale in the figure
    oldlim                    = self.figure.axes[0].get_ylim()
    
    #Order the bounds
    #Order the bounds
    tstarts                   = list(bounds[::2])
    tstops                    = list(bounds[1::2])
    
    #Remember: this method is called to add one interval per time
    newTstart                 = tstarts.pop(-1)
    newTstop                  = tstops.pop(-1)
    newInterval               = dataHandling.TimeInterval(newTstart,newTstop,True)
    
    oldIntervals              = map(lambda x:dataHandling.TimeInterval(x[0],x[1],True),zip(tstarts,tstops))
    
    #Verify if the new interval overlap with the old ones
    merged                    = False
    while(1==1):
      for interval in oldIntervals:
        if(interval.overlapsWith(newInterval)):
          #merge them
          newInterval.merge(interval)
          merged               = True
          #Remove the old interval from the list, and break 
          #(to continue the while loop)
          oldIntervals.pop(oldIntervals.index(interval))
          break
        pass
      pass
      if(merged):
        #Continue the while loop
        merged                = False
        continue
      else:
        #I finished the list of intervals without doing any merger,
        #I can stop
        break  
    pass
    
    oldIntervals.append(newInterval)
    
    #Sort the intervals (which are non-overlapping at this point)
    sortedIntervals           = sorted(oldIntervals,key=lambda x:x.tstart)
    
    nFillers                  = len(fillers)
    
    #Reset the fillers 
    for i in range(nFillers): 
      fillers[i].remove()
    for i in range(nFillers): 
      fillers.pop()
    pass
    
    #Create the new fillers and approximate the boundaries to the closest bins
    j                         = 0
    nIntervals                = int(math.floor(n/2.))  
    for interval in sortedIntervals:
        x1                    = interval.tstart-self.xoffset
        x2                    = interval.tstop-self.xoffset
        
        #Approximate the boundaries to the closest external bins
        indmin                = max(0,np.searchsorted(self.x,x1,side='right')-1)
        indmax                = min(len(self.x)-1,np.searchsorted(self.x,x2,side='left'))
        
        thisx                 = self.x[indmin:indmax+1]
        thisy                 = self.y[indmin:indmax+1]
        
        thisFiller            = self.subfigure.fill_between(self.steppify(thisx),
                                                            self.steppify(thisy,False)*0,
                                                            self.steppify(thisy,False),facecolor=facecolor)
        fillers.append(thisFiller)
        interval.tstart       = min(self.x[indmin:indmax+1])+self.xoffset
        interval.tstop        = max(self.x[indmin:indmax+1])+self.xoffset
        j                    += 2
    pass
    
    self.figure.axes[0].set_ylim(oldlim)
    self.figure.canvas.draw()
    
    #update bounds
    nBounds                   = len(bounds)
    for i in range(nBounds):
      bounds.pop()
    for interval in sortedIntervals:
      bounds.extend([interval.tstart,interval.tstop])
  pass
  
  def steppify(self,arr,isX=True):
    """
    Converts an array to double-length for step plotting
    """
    if isX:
      newarr = np.array(zip(arr[:-1],arr[1:])).ravel()
    else:
      newarr = np.array(zip(arr[:-1],arr[:-1])).ravel()
    return newarr
  
  def printHelp(self):
    pass
#    print '\n                 SELECT TIME INTERVALS '
#    print '-------------------------------------------------------\n'
#    if(self.selectBackground):
#      print ' z + click     select background intervals'
#    if(self.selectSource):
#      print ' x + click     select signal intervals'
#    print ' c + click     reset all selections'
#    print ' w + click     PRINT the selected intervals'
#    print ' q + click     SAVE the intervals and EXIT\n'
#    print '-------------------------------------------------------\n'
#    print ' Other keys:                                   '
#    print ' s       save the canvas (use extension for defining the file format)'
#    print ' p       zoom/pam mode'
#    print ' x       Constrain pan/zoom to x axis (hold the x)'
#    print ' y       Constrain pan/zoom to y axis (hold the y)'
#    print ' o       zoom to rectangular'
#    print ' f       Toggle fullscreen'
#    print ' g       grid on/off'
#    print ' h or r  reset the plot scale'
#    print ' L or k  Toggle x axis scale (log/linear)'
#    print ' l       Toggle y axis scale (log/linear)'
#    print ' TIP: to zoom use the right mouse button in zoom mode (press p)!\n'
  pass
  
  def clickPress(self,event):
    if not self.isNormalMode(event):
      #Ignore event if we are not in normal mode
      return
    if(event.xdata==None or event.ydata==None):
      self.delLines(self.transitoryLines)
      self.curXdata           = 'safetynet'
      self.curYdata           = 'safetynet'
    else:  
      self.curXdata           = event.xdata
      self.curYdata           = event.ydata
  pass
  
  def clickRelease(self,event):
    #print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(event.button, event.x, event.y, event.xdata, event.ydata)    
    #print 'press', event.key
    if not self.isNormalMode(event):
      #Ignore event if we are not in normal mode
      return
    
    #Tolerance
    tol                 = 2.0
    if(event.xdata!=None and self.curXdata!=None):
      deltax            = abs(event.xdata-self.curXdata)
    else:
      deltax            = 1e9
    pass
    if(event.ydata!=None and self.curYdata!=None):
      deltay            = abs(event.ydata-self.curYdata)
    else:
      deltay            = 1e9
    pass
    
    if ( deltax <= tol and deltay <= tol 
       and self.selectBackground and event.button==1): 
        self.lines.append(self.drawVerticalLine(event.xdata))
        #Find the closest bin
        self.backgroundBounds.append(event.xdata+self.xoffset)
        self.drawIntervals(self.backgroundFillers,self.backgroundBounds,'yellow')
    
    elif (deltax <= tol and deltay <= tol 
        and self.selectSource and event.button==1):
        self.lines.append(self.drawVerticalLine(event.xdata))
        self.sourceBounds.append(event.xdata+self.xoffset)
        self.drawIntervals(self.sourceFillers,self.sourceBounds,'red')                    

    self.figure.canvas.draw()
  pass
  
  def cleanClose(self):
    #Close the window
    if(self.figureIsMine):
      self.figure.close()
    else:
      #Do nothing
      pass
      #self.figure.clear()
      #self.figure.canvas.draw()
    pass  
    if(self.locking):
       #This will stop the event loop and allow the calling program to continue
        self.figure.canvas.stop_event_loop()
  pass
    
  def onselect(self,xmin, xmax):
    Xmin                      = xmin
    Xmax                      = xmax
    return Xmin,Xmax
  pass
  
  def wait(self):
    #This will wait until the window is closed
    self.locking              = True
    self.figure.canvas.start_event_loop(0)
    return
  pass  
pass

def writeAsciiFile(bounds,outfile):
  nb                     = len(bounds)
  j                      = 0
  txt                    = ''
  for i in range(int(math.floor(nb/2))):
      txt               += '%.20f %.20f\n' %(bounds[j],bounds[j+1])
      j                 += 2
  pass
  
  fout                   = file(outfile,'w+')
  fout.write(txt)
  fout.close()
pass
