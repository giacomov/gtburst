#This is to get LLE data files (lle, pha and rsp)
#Author: giacomov@slac.stanford.edu

from GtBurst.dataCollector import dataCollector

class GBMdataCollector(dataCollector):
  def __init__(self,grbName,dataRepository=None,localRepository=None,
                    getTTE=True,getCSPEC=True,getRSP=True,getCTIME=True,**kwargs):
    
    dataCollector.__init__(self,'gbm',grbName,dataRepository,localRepository,
                    getTTE,getCSPEC,getRSP,getCTIME,**kwargs)
  pass
      
pass
