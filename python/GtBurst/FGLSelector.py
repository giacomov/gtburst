import os
import numpy

from GtBurst.TriggerSelector import *

from GtBurst.getDataPath import getDataPath

import xml.etree.ElementTree as ET

#Make the dictionary with extended information about sources

txtfile = os.path.join(getDataPath(), '3fgl_extendedData.txt')

if(not os.path.exists(txtfile)):
  raise RuntimeError("You do not have the 3fgl_extendedData.txt file in your data directory!")

data = numpy.recfromtxt(txtfile,delimiter=';',names=True)

#Keys in the 3fgl_extendedData are: 'Source_name', 'Variability_index',
#                                   'ASSOC1','ASSOC2','ASSOC_TEV','CLASS1','Flags'

sources = {}

for row in data:
  sources[row['Source_name']] = row


class FGLSelector(TriggerSelector):
  
    def __init__(self,parent=None, xmlfile=None, **kwargs):
        self.parent           = parent
        
        if(xmlfile is None):
          
          xmlfile             = os.path.join(getDataPath(), 'gll_psc_v16.xml')
        
        pass
        
        self.readFGL(xmlfile, **kwargs)
        
        if(parent!=None):
          #Graphic mode
          self.w                = SubWindow(self.parent,
                                          transient=True,title="Select source",
                                          initialHint="Select a source")
          self.root             = self.w.window
          self.columns          = ['Name','TS','Class1','RA (deg)','Dec (deg)',
                                   'Assoc_1','Assoc_2','Assoc_TEV',
                                   'Variab.index','Flags']
          self.columnsWidths    = [150,80,60,90,90,150,150,150,120,60]
          self.tree             = None
          
          self._setup_widgets(True)
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
          name                    = source.get("name")
          self.data.append([ name.replace(" ",""),
                        "%.3f" % float(source.get("TS_value")),
                        sources[name]["CLASS1"],
                        "%.3f" % float(thisRa),
                        "%.3f" % float(thisDec),
                        sources[name]['ASSOC1'],
                        sources[name]['ASSOC2'],
                        sources[name]['ASSOC_TEV'],
                        sources[name]['Variability_index'],
                        sources[name]['Flags']])
          
        else:
          
          #Cannot analyze extended sources
          continue
