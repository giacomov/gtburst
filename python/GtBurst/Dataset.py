class Dataset(dict):
    def __init__(self,detector,triggerName,triggerTime,triggered=False,angleToGRB=0,
                 llefile='',rspfile='',cspecfile='',ft2file=''):
      dict.__init__(self,{'eventfile': llefile,
                     'rspfile': rspfile,
                     'cspecfile': cspecfile,
                     'ft2file': ft2file})
      self.detector           = detector
      self.triggerName        = triggerName
      self.triggerTime        = triggerTime
      self.angleToGRB         = angleToGRB
      self.triggered          = bool(triggered)
      self.status             = "complete"
      self.descriptions       = {'eventfile': "Event file (LLE or TTE file)",
                                 'rspfile': "Response file (RSP file)",
                                 'cspecfile': "CSPEC file",
                                 'ft2file': "Spacecraft file (FT2)"}
pass
