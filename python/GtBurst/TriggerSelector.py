from Tkinter import *
import tkFont
from tkMessageBox import showerror
#from ttk import *
from Treeview import Treeview
import urllib2
from GtBurst.fontDefinitions import *
from GtBurst.EntryPoint import EntryPoint
from GtBurst.SubWindow import SubWindow
import datetime, math

# Convert RA HH:MM:SS.SSS into Degrees :
def convHMS(ra):
   try :
      sep1 = ra.find(':')
      hh=int(ra[0:sep1])
      sep2 = ra[sep1+1:].find(':')
      mm=int(ra[sep1+1:sep1+sep2+1])
      ss=float(ra[sep1+sep2+2:])
   except:
      raise
   else:
      pass
   
   return(hh*15.+mm/4.+ss/240.)

# Convert Dec +DD:MM:SS.SSS into Degrees :
def convDMS(dec):

   Csign=dec[0]
   if Csign=='-':
      sign=-1.
      off = 1
   elif Csign=='+':
      sign= 1.
      off = 1
   else:
      sign= 1.
      off = 0

   try :
      sep1 = dec.find(':')
      deg=int(dec[off:sep1])
      sep2 = dec[sep1+1:].find(':')
      arcmin=int(dec[sep1+1:sep1+sep2+1])
      arcsec=float(dec[sep1+sep2+2:])
   except:
      raise
   else:
      pass

   return(sign*(deg+(arcmin*5./3.+arcsec*5./180.)/100.))

#Convert a UTC date in MET
def date2met(datestring):
    _missionStart             = datetime.datetime(2001, 1, 1, 0, 0, 0)
       
    sep                       = '-'
    if '/' in datestring : 
      sep                     = '/'
    year,month,day            = datestring.split(sep)
    if len(year)==2: 
      year                    = int(year)+2000
        
    # time given in the string?
    day                       = day.replace('T',':')
    day                       = day.replace(' ',':')
    day,hours,mins,secs       = day.split(':')
    secs                      = float(secs)
    secs_i                    = math.floor(secs)
    decsec                    = secs-secs_i
    
    current                   = datetime.datetime(year=int(year),
                                                  month=int(month),
                                                  day=int(day),
                                                  hour=int(hours),
                                                  minute=int(mins),
                                                  second=int(secs_i))

    diff                      = current -_missionStart
    met                       = diff.days*86400. + diff.seconds + decsec
    
    #Handling leap seconds
    if int(year)>2005:    met+=1
    if int(year)>2008:    met+=1
    if float(met)>362793601.0: met+=1 # June 2012 leap second    
    return met

def sortby(tree, col, descending):
    """Sort tree contents when a column is clicked on."""
    # grab values to sort
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    # reorder data
    data.sort(reverse=descending)
    for indx, item in enumerate(data):
        tree.move(item[1], '', indx)

    # switch the heading so that it will sort in the opposite direction
    tree.heading(col,
        command=lambda col=col: sortby(tree, col, int(not descending)))

class TriggerSelector(object):
    def __init__(self,parent=None,**kwargs):
        self.parent           = parent
        self.downloadList(**kwargs)
        if(self.data==None):
          #Could not download the trigger list!
          return
        if(parent!=None):
          #Graphic mode
          self.w                = SubWindow(self.parent,
                                          transient=True,title="Select trigger",
                                          initialHint="Select a trigger")
          self.root             = self.w.window
          self.columns          = ['Name','Trigger time (MET)','Type','RA (deg)','Dec (deg)','Error radius (deg)','Localizing instrument']
          self.columnsWidths    = [120,150,90,90,90,150,170]
          self.tree             = None
          
          self._setup_widgets()
          self.root.protocol("WM_DELETE_WINDOW", self.done)
        pass
    pass
    
    def downloadList(self,**kwargs):
        if('catalog' in kwargs.keys()):
          f                     = open(kwargs['catalog'])
          text                  = f.read()
          f.close()
        else:
          #Connect to the heasarc and download the list as text with the form:
          #['|trigger_name|trigger_time           |trigger_type|',
          #'+------------+-----------------------+------------+',
          #'|bn080714086 |2008-07-14 02:04:12.053|GRB         |',
          #'|bn080714425 |2008-07-14 10:12:01.838|GRB         |',
          #'|bn080714745 |2008-07-14 17:52:54.023|GRB         |',
          url = "http://heasarc.gsfc.nasa.gov/cgi-bin/W3Browse/w3query.pl?tablehead=name%3dBATCHRETRIEVALCATALOG%5f2%2e0+fermigtrig&Action=Query&Coordinates=%27Equatorial%3a+R%2eA%2e+Dec%27&Equinox=2000&Radius=60&NR=&GIFsize=0&Fields=&varon=trigger%5fname&varon=trigger%5ftime&varon=trigger%5ftype&varon=ra&varon=dec&varon=error_radius&varon=localization_source&sortvar=trigger%5fname&ResultMax=1000000&displaymode=BatchDisplay'"
          if(self.parent!=None):
            window                = Toplevel(self.parent)
            window.transient(self.parent)        
            frame                 = Frame(window)
            frame.pack(fill=BOTH,expand=True,side=TOP)
            label                 = Label(frame,font=LABELFONT,width=60,
                                          text="Downloading trigger list from HEASARC website...\n\n")
            label.pack(expand=True,fill=BOTH,side=LEFT)
            window.update_idletasks()
            self.parent.update_idletasks()
          pass
          
          try:
            response              = urllib2.urlopen(url,None,timeout=60)
          except:
            self.triggerName        = None
            self.triggerTime        = None
            self.ra                 = None
            self.dec                = None
            self.data               = None
            
            if(self.parent!=None):
              window.destroy()
              showerror("No connection","You do not seem to be connected to the internet, or problem with the HEASARC server. Cannot download list of triggers, you have to specify your trigger manually",
                         parent=self.parent)
            else:
              raise RuntimeError("You do not seem to be connected to the internet, or problem with the HEASARC server. Cannot download list of triggers")
            
            return
          pass
          
          text                  = response.read()
          f                     = open("trigcat.txt",'w+')
          f.write(text)
          f.close()
        pass
        
        self.data             = map(lambda x:x.strip().split("|")[1:-1],text.split("\n")[3:-2])
        #Convert RA, Dec from hh mm ss to decimal, and the trigger time from ISO UTC to MET
        for i in range(len(self.data)):
          triggerDate         = self.data[i][1].strip()
          self.data[i][1]     = "%12.3f" % date2met(triggerDate)
          ra                  = self.data[i][3].strip().replace(' ',':') #RA in HH:DD:MM.SSS format
          self.data[i][3]     = " %5.3f" % convHMS(ra)
          dec                 = self.data[i][4].strip().replace(' ',':')
          self.data[i][4]     = " %5.3f" % convDMS(dec)
        #Remove all spaces
        self.data             = map(lambda x:map(lambda y:y.replace(" ",''),x),self.data)
        if(self.parent!=None):
          window.destroy()
    pass
    
    def _setup_widgets(self):
        self.filterFrame      = Frame(self.root)
        self.filterFrame.grid(row=0,column=0)
        triggerTypes          = list(set(map(lambda x:x[2],self.data)))
        triggerTypes.sort()
        triggerTypes.insert(0,'All')
        self.filter           = EntryPoint(self.filterFrame,labeltext="Trigger type filter: ",
                                           textwidth=20,possibleValues=triggerTypes)
        self.filter.variable.trace('w',lambda name, index, mode, sv=self.filter.variable: self.apply_filter(sv))
        self.container        = Frame(self.root)
        self.container.grid(row=1,column=0)
        self.root.grid_columnconfigure(0,weight=1)
        self.root.grid_rowconfigure(0,weight=1)
        
        self._setup_tree()
        self.buttonFrame = Frame(self.root)
        self.buttonFrame.grid(row=2,column=0)
        self.button = Button(self.buttonFrame,text="Done",command=self.done)
        self.button.grid(row=0,column=0)
        self.button2 = Button(self.buttonFrame,text="Cancel",command=self.cancel)
        self.button2.grid(row=0,column=1)
        msg                   = Label(self.root,wraplength="4i", justify="left", anchor="n",
                                  text=("Click on a column to sort the table (or invert the sorting)"))
        msg.grid(row=3,column=0,sticky="NWSE")    
    pass
    
    def done(self,item=None):
      if(item==None):
        try:
          item                    = self.tree.selection()[0]
        except:
          showerror("No selection done","You have to select a trigger!",parent=self.root)
          return
        pass
      pass
      
      if(self.parent!=None):
        par                     = self.tree.item(item,"values")
      else:
        #No GUI mode
        try:
          par                     = filter(lambda x:x[0].replace("bn","").replace("GRB","").replace("SF","")==item.replace("bn","").replace("GRB","").replace("SF",""), self.data)[0]
        except:
          raise ValueError("Trigger %s not found in the trigger catalog" %(item))
      self.triggerName        = par[0]
      self.triggerTime        = par[1]
      self.ra                 = par[3]
      self.dec                = par[4]
      
      if(self.parent!=None):
        self.root.destroy()
        self.parent.grab_set()
    pass
    
    def cancel(self):
      self.triggerName        = None
      self.triggerTime        = None
      self.ra                 = None
      self.dec                = None
      self.root.destroy()
    pass
    
    def apply_filter(self,stringvar):
      self._setup_tree(stringvar.get())
    pass
    
    def _setup_tree(self,curfilter='All'):
        if(self.tree!=None):
          self.tree.destroy()
        # XXX Sounds like a good support class would be one for constructing
        #     a treeview with scrollbars.
        self.tree             = Treeview(self.container,columns=self.columns, show="headings")
        vsb                   = Scrollbar(self.container,orient="vertical", command=self.tree.yview)
        hsb                   = Scrollbar(self.container,orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        for col,width in zip(self.columns,self.columnsWidths):
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: sortby(self.tree, c, 1))
            # XXX tkFont.Font().measure expected args are incorrect according
            #     to the Tk docs
            self.tree.column(col, width=width)
        
        self.items            = []
        if(curfilter!='All'):
          dataToDisplay         = filter(lambda x:x[2]==curfilter,self.data)   
        else:
          dataToDisplay         = self.data
        pass
        
        for item in dataToDisplay:
            self.items.append(self.tree.insert('', 'end', values=item))
        self.tree.bind("<Double-1>", self.OnDoubleClick)
    pass
    
    def OnDoubleClick(self,event):
        #import pdb;pdb.set_trace()
        #item = self.tree.selection()[0]
        #print "you clicked on", self.tree.item(item,"values")[0]
        #self.tree.set(item,0,'TEST')
        self.done()
    pass  
        
if __name__ == "__main__":
    a                         = TriggerSelector()
    print a.triggerName
    
