#!/usr/bin/env python

from multiprocessing import Pool
import numpy as np
import tempfile
import os
import subprocess
import pyfits

from gt_apps import expMap

def expmap(square):

    '''This is the atomic function that actually runs in the seperate
    threads.  The input is a python list.  The first element is a list
    of two arrays giving the x and y points.  The second through last
    elements are the scfile, evfile, expcube, nlong, nlat, irfs,
    srcrad and nenergies.  This function creates a temporary file for
    the output and returns that file's name.'''

    print "Starting calculation of region {},{} to {},{}".format(square[0][0][0],
                                                                 square[0][1][0],
                                                                 square[0][0][1],
                                                                 square[0][1][1])
    osfilehandle,outfilename = tempfile.mkstemp(suffix=".fits")
    expMap['nlongmin'] = "{:,.0f}".format(float(square[0][0][0]))
    expMap['nlongmax'] = "{:,.0f}".format(float(square[0][0][1]))
    expMap['nlatmin'] = "{:,.0f}".format(float(square[0][1][0]))
    expMap['nlatmax'] = "{:,.0f}".format(float(square[0][1][1]))
    expMap['scfile'] = square[1]
    expMap['evfile'] = square[2]
    expMap['expcube'] = square[3]
    expMap['nlong'] = square[4]
    expMap['nlat'] = square[5]
    expMap['irfs'] = square[6]
    expMap['srcrad'] = square[7]
    expMap['nenergies'] = square[8]
    expMap['outfile'] = outfilename
    expMap['submap'] = "yes"
    expMap['chatter'] = 0
    expMap.run(print_command=False)
    print "Completed calculation of region {},{} to {},{}".format(square[0][0][0],
                                                                  square[0][1][0],
                                                                  square[0][0][1],
                                                                  square[0][1][1])
                
    return outfilename

def expsum(filenames, Outfile, SaveTemp):

    '''This function takes a list of exposure maps and adds them together.
    If there is only one file to be added, it just copies it to the
    outfile.  If there is more than one, it uses pyfits to open them all
    up, sum the first hdus (the data) and then replaces the first file's
    primary hdu with this summed data and writes it to the output file.'''

    if len(filenames) <= 1:
        subprocess.call(["cp", filenames[0], Outfile])
    else:
        expmap_files = [pyfits.open(filename) for filename in filenames]
        summed_expmap_hdu = (np.array([expmap_file[0].data for expmap_file in expmap_files])).sum(axis=0)
        expmap_files[0][0].data = summed_expmap_hdu
        expmap_files[0][0].update_header()
        expmap_files[0].writeto(Outfile, clobber='True')
        for expmap_file in expmap_files: expmap_file.close()
        
    if SaveTemp:
        print "Did not delete the following temporary files:"
        print filenames
    else:
        print "Deleting temporary files..."
        for filename in filenames:
            os.remove(filename)

def gtexpmap_mp(nlong, nlat, xbins, ybins, SCFile, EVFile, ExpCube, 
                IRF, srcrad, nenergy, OutFile, SaveTemp):

    '''This function determines the x,y pairs for dividing up the jobs on
    the sky.  It then creates a list of tuples conatining all of the
    information needed for the atomic expmap function.'''

    bins = xbins*ybins

    if np.mod(nlong,xbins) or np.mod(nlat,ybins):
        print "The number of x and y bins must fit evenly into the number of long or lat points."
        return

    stepx = nlong/xbins
    stepy = nlat/ybins

    x_start = np.linspace(0,nlong-stepx,xbins)
    x_stop = np.linspace(stepx,nlong,xbins)
    y_start = np.linspace(0,nlat-stepy,ybins)
    y_stop = np.linspace(stepy,nlat,ybins)

    pairs = [(x_pair,y_pair) for x_pair in np.column_stack((x_start,x_stop)) for y_pair in np.column_stack((y_start,y_stop))]
    SQ = [(row, SCFile,EVFile,ExpCube,nlong,nlat,IRF,srcrad,nenergy) for row in pairs]    

    pool = Pool(processes=bins)      
    print "Spawning {} jobs...".format(bins)
    filenames = pool.map(expmap,SQ)
    print "Combining temporary files..."
    expsum(filenames, OutFile, SaveTemp)

def cli():

    helpString = "Submits the gtexpmap program as sperate threads via python and\
                  joins up the resulting temporary exposure maps at the end\
                  resulting in a single exposure map for the input event file.\
                  This greatly reduces the running time. For more details on \
                  gtexpmap see the gtexpmap help file.  Note that the checksum \
                  and datasum are incorrect for the final file.  The number of \
                  spawned jobs is equal to xbins x ybins."

    import argparse

    parser = argparse.ArgumentParser(description=helpString)
    parser.add_argument("nlong", type=int, help="Number of longitude points.  See gtexpmap help for more information.")
    parser.add_argument("nlat", type=int, help="Number of latitude points.  See gtexpmap help for more information.")
    parser.add_argument("xbins", type=int, help="The number of bins along the x-axis.  Must divide evenly into nlong.")
    parser.add_argument("ybins", type=int, help="The number of bins along the y-axis.  Must divide evenly into nlat.")
    parser.add_argument("sfile", help="The spacecraft data file. See gtexpmap help for more information.")
    parser.add_argument("evfile", help="Input event file.  See gtexpmap help for more information.")
    parser.add_argument("expcube", help="Input livetime cube.  See gtexpmap help for more information.")
    parser.add_argument("IRFS", help="IRFs to use.  See gtexpmap help for more information.")
    parser.add_argument("srcrad", help="Radius.  See gtexpmap help for more information.")
    parser.add_argument("nenergies", help="Number of energy slices.  See gtexpmap help for more information.")
    parser.add_argument("outfile", help="Output file name.")

    parser.add_argument("--savetmp", default = False, help="Save the temporary files (default is False).")
    
    args = parser.parse_args()

    gtexpmap_mp(args.nlong, args.nlat, args.xbins, args.ybins, args.sfile, args.evfile, args.expcube, 
                args.IRFS, args.srcrad, args.nenergies, args.outfile, args.savetmp)


if __name__ == '__main__': cli()
