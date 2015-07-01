import os

from GtBurst.TriggerSelector import *

from GtBurst.getDataPath import getDataPath

import xml.etree.ElementTree as ET

class FGLSelector(TriggerSelector):
  
    def __init__(self,parent=None, xmlfile=None, **kwargs):
        self.parent           = parent
        
        if(xmlfile is None):
          
          xmlfile             = os.path.join(getDataPath(), 'gll_psc_v07.xml')
        
        pass
        
        self.readFGL(xmlfile, **kwargs)
        
        if(parent!=None):
          #Graphic mode
          self.w                = SubWindow(self.parent,
                                          transient=True,title="Select source",
                                          initialHint="Select a source")
          self.root             = self.w.window
          self.columns          = ['Name','Type','TS','RA (deg)','Dec (deg)']
          self.columnsWidths    = [150,100,90,90,90]
          self.tree             = None
          
          self._setup_widgets(False)
          self.root.protocol("WM_DELETE_WINDOW", self.done)
        pass
    pass
    
    def readFGL(self, xmlfile):
      
      tree                      = ET.parse(xmlfile)
      root                      = tree.getroot()
      
      self.data                 = []
      
      for source in root.findall('source'):      
        
        spatialModel            = source.findall('spatialModel')[0]
        
        if(source.get('type')=='PointSource'):
          
          #Get coordinates of this point source
          coords                  = {}
          
          for p in spatialModel.iter('parameter'):
          
            coords[p.get('name').lower()] = float(p.get('value'))
          
          thisRa                  = coords['ra']
          thisDec                 = coords['dec']
          
          self.data.append([ source.get("name").replace(" ",""), 
                        source.get("type"),
                        source.get("TS_value"),
                        thisRa,
                        thisDec])
          
        else:
          
          #Cannot analyze extended sources
          continue
