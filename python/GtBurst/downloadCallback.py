import ftplib
import sys

class Callback(object):
  def __init__(self, totalsize, fp, meter):
    self.totalsize            = totalsize
    self.fp                   = fp
    self.m                    = meter
  def __call__(self, data):
    self.fp.write(data)
    self.received             = self.fp.tell()
    ratio                     = self.received/self.totalsize
    
    if(self.m!=None):
      if(ratio > 1):
        self.m.set(1)
      else:
        self.m.set(ratio)
      pass
    else:
      if((ratio%5)==0):
        print(".%s." %(ratio))
  pass 
pass

class get_size(object):
  def __call__(self,listing):
    self.size                 = float(listing.split()[4])

if __name__ == '__main__':
  host                        = 'legacy.gsfc.nasa.gov'
  src                         = '/fermi/data/gbm/daily/2008/12/01/current/glg_ctime_b0_081201_v00.pha'
  c                           = ftplib.FTP(host)
  c.set_debuglevel(0)
  c.login()
  g                           = get_size()
  c.dir(src,g)
  size                        = g.size*1024
  dest                        = src.split("/")[-1]
  f                           = open(dest, 'wb+')
  w                           = Callback(size, f)
  print("Downloading %s bytes..." %(size))
  c.retrbinary('RETR %s' % src, w)
  f.close()
  c.quit()
