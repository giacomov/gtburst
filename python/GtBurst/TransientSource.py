import collections

class TransientSource(dict):
  def __init__(self,name='',ra='',dec='',date=''):
    dict.__init__(self,{'name': name,
                     'ra': ra,
                     'dec': dec,
                     'date': date})
    self.descriptions          = collections.OrderedDict()
    self.descriptions['name']  = "Trigger name"
    self.descriptions['ra']    = "R.A. (J2000)"
    self.descriptions['dec']   = "Dec. (J2000)"
    self.descriptions['date']  = "Trigger date (MET)"                
    
    self.headerKeyword         = {'name': "OBJECT",
                                 'ra': "RA_OBJ",
                                 'dec': "DEC_OBJ",
                                 'date': "TRIGTIME"}
  pass  
pass
