from pyLikelihood import JulianDate, SolarSystem
import os

#This converts from MET to Julian Date
def _jd_from_MET( met ):
    jd=JulianDate((JulianDate_missionStart().seconds()
                           + met)/JulianDate.secondsPerDay)
    return jd

def getSunPosition( met ):
    #environment variable (you need FTOOLS installed and configured)
    os.environ['TIMING_DIR']=os.path.join(os.environ['HEADAS'],"refdata")
    #Get the sun direction
    sun=SolarSystem(SolarSystem.SUN)
    SunSkyDir = sun.direction(_jd_from_MET(met))
    return SunSkyDir
