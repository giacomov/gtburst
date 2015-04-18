import math
import numpy as np

#Angles of NaI detectors in spacecraft coordinates
#(from Meegan et al.)
#[zenith, azimuth]
DetDir        = {}
DetDir['n0']  = [20.58, 45.89]
DetDir['n1']  = [45.31, 45.11]
DetDir['n2']  = [90.21, 58.44]
DetDir['n3']  = [45.24, 314.87]
DetDir['n4']  = [90.27, 303.15]
DetDir['n5']  = [89.79, 3.35]
DetDir['n6']  = [20.43, 224.93]
DetDir['n7']  = [46.18, 224.62]
DetDir['n8']  = [89.97, 236.61]
DetDir['n9']  = [45.55, 135.19]
DetDir['na']  = [90.42, 123.73]
DetDir['nb']  = [90.32, 183.74]
#Angles of BGO detectors, just to mean they are in two opposite directions     
DetDir['b0']  = [90.0, 0.00]
DetDir['b1']  = [90.0, 180.00]
#Of course the LAT is at 0,0
DetDir['LAT-LLE'] = [0.0,0.0]
DetDir['LAT'] = [0.0,0.0]

def getDetectorAngle(ra_scx,dec_scx,ra_scz,dec_scz,sourceRa,sourceDec,detector):
  if detector in DetDir.keys():
    t                         = DetDir[detector][0]
    p                         = DetDir[detector][1]
    ra,dec                    = getRaDec(ra_scx,dec_scx,ra_scz,dec_scz,t,p)
    return getAngularDistance(sourceRa,sourceDec,ra,dec)
  else:
    raise ValueError('Detector %s is not recognized' %(detector))        
pass


def getAngularDistance(ra1,dec1,ra2,dec2):
  dlat = np.deg2rad(dec2 - dec1)
  dlon = np.deg2rad(ra2 - ra1)
  dec1 = np.deg2rad(dec1)
  dec2 = np.deg2rad(dec2)
  a = np.sin(dlat/2.)*np.sin(dlat/2.) + np.cos(dec1)*np.cos(dec2)*np.sin(dlon/2.)*np.sin(dlon/2.)
  c  = 2*np.arctan2(np.sqrt(a), np.sqrt(1.-a))
  return np.rad2deg(c)

def _getNaIDirection(self,detectors):
  DetDir  = {}
  outDetDir     = {}
  for det in detectors:
    outDetDir[det] = DetDir[det] 
  pass
  return outDetDir
pass

def getThetaPhi(ra_scx,dec_scx,ra_scz,dec_scz,RA,DEC):
  v0                          = getVector(RA,DEC)
  vx                          = getVector(ra_scx,dec_scx)
  vz                          = getVector(ra_scz,dec_scz)
  vy                          = Vector(vz.cross(vx))
  
  theta                       = math.degrees(v0.angle(vz))    
  phi                         = math.degrees(math.atan2(vy.dot(v0),vx.dot(v0)))
  if phi<0: phi+=360
  return theta, phi

def getRaDec(ra_scx,dec_scx,ra_scz,dec_scz,theta,phi):
  vx                          = getVector(ra_scx,dec_scx)
  vz                          = getVector(ra_scz,dec_scz)
  
  vxx                         = Vector(vx.rotate(phi,vz))  
  vy                          = Vector(vz.cross(vxx))
  
  vzz                         = vz.rotate(theta,vy)
   
  ra                          = math.degrees(math.atan2(vzz[1],vzz[0]))
  dec                         = math.degrees(math.asin(vzz[2]))
  
  if(ra<0):
    ra                       += 360.0
  return ra,dec  
pass

def getVector(ra,dec):
  ra1                         = math.radians(ra)
  dec1                        = math.radians(dec)
  
  cd                          = math.cos(dec1)
  
  return Vector([math.cos(ra1) * cd, 
                          math.sin(ra1) * cd,
                          math.sin(dec1)])

class Vector(object):
  def __init__(self,array):
    self.vector               = np.array(array)
  pass
  
  def rotate(self,angle,axisVector):
    ang                       = math.radians(angle)
    matrix                    = self._getRotationMatrix(axisVector.vector,ang)
    #print matrix
    return np.dot(matrix,self.vector)
  
  def cross(self,vector):
    return np.cross(self.vector,vector.vector)
    
  def _getRotationMatrix(self,axis,theta):
    axis                      = axis/np.sqrt(np.dot(axis,axis))
    a                         = np.cos(theta/2)
    b,c,d                     = -axis*np.sin(theta/2)
    return np.array([[a*a+b*b-c*c-d*d, 2*(b*c+a*d),2*(b*d-a*c)],
                     [2*(b*c-a*d), a*a+c*c-b*b-d*d, 2*(c*d+a*b)],
                     [2*(b*d+a*c), 2*(c*d-a*b), a*a+d*d-b*b-c*c]])           
   
  def norm(self):
     return np.linalg.norm(self.vector)
  
  def dot(self,vector):
    return np.dot(self.vector,vector.vector)
   
  def angle(self,vector):
     return math.acos(np.dot(self.vector,vector.vector)/(self.norm()*vector.norm()))
pass


#The following are only for testing purposes, they won't be used
#by the final user (they require ROOT)
def getVectorROOT(ra,dec):
    import ROOT
    ra1  = math.radians(ra)
    dec1 = math.radians(dec)    
    # here we construct the cartesian equatorial vector
    dir = ROOT.TVector3(math.cos(ra1)*math.cos(dec1), math.sin(ra1)*math.cos(dec1) , math.sin(dec1))
    return dir
pass

def getRaDecROOT(ra_scx,dec_scx,ra_scz,dec_scz,theta,phi):
  import ROOT
  vx    = getVectorROOT(ra_scx,dec_scx)
  vz    = getVectorROOT(ra_scz,dec_scz)
  
  vx.Rotate(math.radians(phi),vz)
  vy    = vz.Cross(vx)
  
  #matrixROOT                  = ROOT.TRotation()
  #matrixROOT.Rotate(math.radians(phi),vz)
  
  vz.Rotate(math.radians(theta),vy)
  
  dec = math.degrees(math.asin(vz.z()))
  ra  = math.degrees(math.atan2(vz.y(),vz.x()))
  if ra<0: ra+=360
  return ra,dec
pass

def getBoundingCoordinates(lon,lat,radius):
  '''
  Finds the smallest "rectangle" which contains the given Region Of Interest.
  It returns lat_min, lat_max, dec_min, dec_max. If a point has latitude
  within lat_min and lat_max, and longitude within dec_min and dec_max,
  it is possibly contained in the ROI. Otherwise, it is certainly NOT 
  within the ROI.
  '''
  radLat                      = np.deg2rad(lat)
  radLon                      = np.deg2rad(lon)
  
  radDist                     = np.deg2rad(radius)
  
  minLat                      = radLat - radDist
  maxLat                      = radLat + radDist
  
  MIN_LAT                     = np.deg2rad(-90.0)
  MAX_LAT                     = np.deg2rad(90.0)
  MIN_LON                     = np.deg2rad(-180.0)
  MAX_LON                     = np.deg2rad(180.0)
  
  if(minLat > MIN_LAT and maxLat < MAX_LAT):
    pole                      = False
    
    deltaLon                  = np.arcsin(np.sin(radDist)/np.cos(radLat))
    
    minLon                    = radLon - deltaLon
    maxLon                    = radLon + deltaLon
    
    if(minLon < MIN_LON):
      minLon                 += 2.0*np.pi
    if(maxLon > MAX_LON):
      maxLon                 -= 2.0*np.pi
    
    #In FITS files the convention is to have longitude from 0 to 360, instead of
    #-180,180. Correct this
    if(minLon < 0):
      minLon                   += 2.0*np.pi
    if(maxLon < 0):
      maxLon                   += 2.0*np.pi
  else:
    pole                      = True
    #A pole is within the ROI
    minLat                    = max(minLat,MIN_LAT)
    maxLat                    = min(maxLat,MAX_LAT)
    minLon                    = 0
    maxLon                    = 2.0*np.pi
  pass
  
  #Inversion can happen due to boundaries, so make sure min and max are right
  #minLatf,maxLatf             = min(minLat,maxLat),max(minLat,maxLat)
  #minLonf,maxLonf             = min(minLon,maxLon),max(minLon,maxLon)
  
  return np.rad2deg(minLon), np.rad2deg(maxLon), np.rad2deg(minLat), np.rad2deg(maxLat), pole
  
pass

