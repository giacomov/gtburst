#!/usr/bin/env python

from multiprocessing import Pool
import numpy as np
import pyfits
import tempfile
import os
import subprocess

from gt_apps import diffResps,filter

def diffrsp(times):

    '''This is the atomic function that actually runs in the seperate
    threads.  It takes a list as input where the first element is
    tmin, second is tmax, third is the spacecraft file, fourth is the
    event file, fifth is the source model and sixth is the IRF.  It
    first uses gtselect with wide open cuts to divide up the event
    file then it runs gtdiffrsp on that event file.  The temporary
    event file is deleted automatically.  The function returns the
    name of the created event file which can be combined with other
    files and/or deleted later.'''

    print "Starting calculation on interval {} to {}".format(times[0],times[1])

    osfilehandle,outfilename = tempfile.mkstemp(suffix=".fits")
    filter['rad'] = "INDEF"
    filter['evclass'] = 0
    filter['evclsmin'] = 0
    filter['evclsmax'] = 10
    filter['infile'] = times[3]
    filter['outfile'] = outfilename
    filter['ra'] = "INDEF"
    filter['dec'] = "INDEF"
    filter['tmin'] = times[0]
    filter['tmax'] = times[1]
    filter['emin'] = 0
    filter['emax'] = 400000
    filter['zmax'] = 180
    filter['convtype'] = -1
    filter['chatter'] = 0
    filter.run(print_command=False)

    diffResps['evfile'] = outfilename
    diffResps['scfile'] =  times[2]
    diffResps['srcmdl'] = times[4]
    diffResps['irfs'] = times[5]
    diffResps['chatter'] = 0
    diffResps.run(print_command=False)
    print "Completed calculation of interval {} to {}".format(times[0],times[1])
    return outfilename

def eventsum(filenames, Outfile, SaveTemp):

    '''This function takes a list of event files and sums them up using
    gtselect.  It first checks to see if there's only one temporary
    file.  If so, it just copies that to the output file.  If not, it
    creates a temporary file that lists the individual event files
    and operates gtselect on them.'''

    if len(filenames) <= 1:
        subprocess.call(["cp", filenames[0], Outfile])
    else:
        fileListfile = tempfile.NamedTemporaryFile()
        for filename in filenames:
            fileListfile.file.write(filename + "\n")
        fileListfile.flush()
        filter['rad'] = "INDEF"
        filter['evclass'] = 0
        filter['evclsmin'] = 0
        filter['evclsmax'] = 10
        filter['infile'] = "@"+fileListfile.name
        filter['outfile'] = Outfile
        filter['ra'] = "INDEF"
        filter['dec'] = "INDEF"
        filter['tmin'] = "INDEF"
        filter['tmax'] = "INDEF"
        filter['emin'] = 0
        filter['emax'] = 400000
        filter['zmax'] = 180
        filter['convtype'] = -1
        filter['chatter'] = 0
        filter.run(print_command=False)

    if SaveTemp:
        print "Did not delete the following temporary files:"
        print filenames
    else:
        print "Deleting temporary files..."
        for filename in filenames:
            os.remove(filename)


def gtdiffrsp_mp(bins, SCFile, EVFile, OutFile, SaveTemp, SrcModel,IRF):

    '''This function looks at the start and stop times in an event file
    and splits the time into chunks.  It then submits jobs based upon
    those start and stop times.'''

    print "Opening event file to determine break points..."
    hdulist = pyfits.open(EVFile)
    tstart = hdulist[0].header['TSTART']
    tstop = hdulist[0].header['TSTOP']
    hdulist.close()
    starts, step = np.linspace(tstart,tstop,bins,endpoint=False, retstep=True)
    stops = starts + step
    scfiles = [SCFile for st in starts]
    evfiles = [EVFile for st in starts]
    srcmdls = [SrcModel for st in starts]
    irfs =  [IRF for st in starts]

    pool = Pool(processes=bins)      
    times = np.array([starts,stops,scfiles,evfiles,srcmdls,irfs])

    print "Spawning {} jobs...".format(bins)
    tempfilenames = pool.map(diffrsp,times.transpose())
    print "Combining temporary files..."
    eventsum(tempfilenames, OutFile, SaveTemp)

def cli():

    helpString = "Submits the gtdiffrsp program as sperate threads via python and\
                  joins up the resulting temporary files at the end resulting in \
                  a single file.  This greatly reduces the running time. For more\
                  details on gtdiffrsp see the gtdiffrsp help file."

    import argparse

    parser = argparse.ArgumentParser(description=helpString)
    parser.add_argument("jobs", type=int, help="The number of jobs you wish to spawn (usually the number of cores on your machine).")
    
    parser.add_argument("evfile", help="Input event file.  See gtdiffrsp help for more information.")
    parser.add_argument("scfile", help="Spacecraft file.  See gtdiffrsp help for more information.")
    parser.add_argument("srcmdl", help="The source model file to use. See gtdiffrsp help for more information.")    
    parser.add_argument("irf", help="The IRFs to use. See gtdiffrsp help for more information.")    
    parser.add_argument("outfile", help="Output file name.")

    parser.add_argument("--savetmp", default = False, help="Save the temporary files (default is False).")

    args = parser.parse_args()

    gtdiffrsp_mp(args.jobs, args.scfile, args.evfile, args.outfile, args.savetmp, args.srcmdl, args.irf)

if __name__ == '__main__': cli()

    
