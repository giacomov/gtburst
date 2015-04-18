#!/usr/bin/env python

from multiprocessing import Pool
import os
import subprocess
import pyfits
import sys
import pickle
import argparse

import pyLikelihood as pyLike
from UnbinnedAnalysis import *
from gt_apps import GtApp

""" The overall structure and many of the underlying algorithms used
here are based on and sometimes blantenly copied from batch_tssmap.py
which was written by J. Chiang """

def resolve_fits_files(infile):

    '''This function returns a properly formatted infile loaation since
    most of the analysis is done in subdirectories and the actual support
    files are in ../.'''

    infile = os.path.abspath(infile)
    foo = infile.strip('@')
    try:
        pyfits.open(foo)
    except IOError:
        return [item.strip() for item in open(foo)]
    return [infile]

def getPointSource(like):

    '''This function creats a test source object for use in the likelihood
    analysis at a specific pixel.'''

    test_src = pyLike.PointSource(0, 0, like.observation.observation)
    pl = pyLike.SourceFactory_funcFactory().create('PowerLaw')
    pl.setParamValues((1, -2, 100))
    indexPar = pl.getParam('Index')
    indexPar.setBounds(-3.5, -1)
    pl.setParam(indexPar)
    prefactor = pl.getParam('Prefactor')
    prefactor.setBounds(1e-10, 1e3)
    prefactor.setScale(1e-9)
    pl.setParam(prefactor)
    test_src.setSpectrum(pl)
    return test_src

def runLikelihood(subdir, tpl_file):

    '''This runction runs the likelihood code on a set of pixels in a
    subdirectory.  It takes as input the subdirectory to work on and a
    template counts map.  It reads it's configuration from a pickle
    file (par.pck) that should be located in the subdirectory and the
    pixel locations from another pickle file (pixel.pck).  It then
    creats an overall likelihood object, does a quick global fit and
    then loops over the pixels.  At each pixel, it creats a test
    source, fits that source, calculates the TS of the source and
    writes the results to an output file in the subdirectory called
    ts_results.dat.'''


    parfile = open("par.pck", "r")
    pars = pickle.load(parfile)

    pixelfile = open("pixel.pck", "r")
    pixels = pickle.load(pixelfile)

    pixel_coords = PixelCoords(tpl_file)

    obs = UnbinnedObs(resolve_fits_files(pars['evfile']),
                      resolve_fits_files(pars['scfile']),
                      expMap='../'+pars['expmap'],
                      expCube='../'+pars['expcube'],
                      irfs=pars['irfs'])

    like = UnbinnedAnalysis(obs, '../'+pars['srcmdl'], pars['optimizer'])
    like.setFitTolType(pars['toltype'])
    like.optimize(0)
    loglike0 = like()
    test_src = getPointSource(like)
    target_name = 'testSource'
    test_src.setName(target_name)
    outfile = 'ts_results.dat'
    finished_pixels = []
    if os.path.isfile(outfile):
        input = open(outfile, 'r')
        for line in input:
            tokens = line.strip().split()
            ij = int(tokens[0]), int(tokens[1])
            finished_pixels.append(ij)
        input.close()
    output = open(outfile, 'a')
    for indx, i, j in pixels:
        if (i, j) in finished_pixels:
            continue
        ra, dec = pixel_coords(i, j)
        test_src.setDir(ra, dec, True, False)
        like.addSource(test_src)
        like.optimize(0)
        ts = -2*(like() - loglike0)
        output.write("%3i  %3i %.3f  %.3f  %.5f\n" % (i, j, ra, dec, ts))
        output.flush()
        like.deleteSource(target_name)
    output.close()

def launchJobs(SQ):

    '''This function actually launches a job.  It takes the configuration
    square as input, creates the subdirectories, writes the par and
    pixel pickle files and then launches the code again with the
    subdirectory and template file as options with the number of jobs
    requested.'''

    subdir = SQ[0]
    pars = SQ[1]
    pixels = SQ[2]
    tpl_file = SQ[3]

    os.chdir(subdir)
    
    parfile = open("par.pck", "w")
    pickle.dump(pars, parfile)
    parfile.close()

    pixelfile = open("pixel.pck", "w")
    pickle.dump(pixels, pixelfile)
    pixelfile.close()

    if sys.argv[0][0] == '/':
        this_arg = sys.argv[0]
    else:
        this_arg = '../'+sys.argv[0]
    
    command = ("python %s runLike %s %s"
               % (this_arg,subdir, tpl_file))
    sys.stdout.write("partition %s: " % subdir)
    print command
    sys.stdout.flush()
    subprocess.call(command.split())
    
def _readlines(fileobj, comment=''):

    '''This function read a line in the saved data in the
    subdirectories.'''

    lines = []
    for line in fileobj:
        if ((comment != '' and line.find(comment) == 0)
            or len(line.strip()) == 0):
            continue
        if comment != '':
            line = line.split(comment)[0].strip()
        lines.append(line)
    return lines

def read_data(file, delimiter=None, nskip=0, ncols=0, nmax=0, comment="#"):

    '''This function reads in the saved data in the subdirectories.'''

    data = _readlines(open(file), comment=comment)
    if nmax == 0:
        nmax = len(data) - nskip
    data = data[nskip:nskip+nmax]
    if ncols == 0:
        ncols = len(data[0].split(delimiter))
    columns = []
    for i in range(ncols):
        columns.append([])
    for line in data:
        datum = line.split(delimiter)
        for i in range(ncols):
            if (datum[i].find('.') == -1 and datum[i].find('e') == -1
                and datum[i].find('E') == -1):
#                columns[i].append(int(datum[i]))
                columns[i].append(float(datum[i]))
            else:
                columns[i].append(float(datum[i]))
    for i in range(ncols):
        columns[i] = num.array(columns[i])
    return tuple(columns)

class PixelCoords():

    '''This class retuns the pixel coordinates of a fits file.'''

    def __init__(self, template_file):
        self.proj = pyLike.SkyProj(template_file)
        template = pyfits.open(template_file)
        self.nx = template[0].header['NAXIS1']
        self.ny = template[0].header['NAXIS2']
    def __call__(self, i, j):
        return self.proj.pix2sph(i+1, j+1)

class BatchTsMap(object):

    '''Generates a TS map on a multicore machine.'''


    def __init__(self, pars, num_queues=40, tpl_file='cmap_tpl.fits',savetmp=True):

        '''Initializes the object and sets up the number of queues and stores
        all the parameters.'''

        self.num_queues = num_queues
        self.tpl_file = tpl_file
        self.savetmp = savetmp
        self.pars = pars

        self._createTemplate()
        self.pixel_coords = PixelCoords(self.tpl_file)
        self.njobs = min(self.num_queues, self.pixel_coords.ny)
        self.subdirs = [("%03i" % i) for i in range(self.njobs)]
        
    def _createTemplate(self):
        pars = self.pars
        gtbin = GtApp('gtbin')
        gtbin.run(algorithm='CMAP', evfile=pars['evfile'],
                  scfile=pars['scfile'], outfile=self.tpl_file,
                  nxpix=pars['nxpix'], nypix=pars['nypix'],
                  binsz=pars['binsz'], coordsys=pars['coordsys'],
                  xref=pars['xref'], yref=pars['yref'], axisrot=0,
                  proj=pars['proj'], chatter=0, clobber='yes')

    def getPixels(self, partition):
        nx, ny = self.pixel_coords.nx, self.pixel_coords.ny
        nsize = nx*ny/self.njobs
        if nx*ny % self.njobs != 0:
            nsize += 1
        pixels = []
        indx = 0
        for i in range(nx):
            for j in range(ny):
                if indx >= nsize*partition and indx < nsize*(partition + 1):
                    pixels.append((indx, i, j))
                indx += 1
        return pixels

    def prepareSubdirs(self):
        for subdir in self.subdirs:
            try:
                os.mkdir(subdir)
            except OSError:
                pass

    def merge_results(self):
        tsmap = pyfits.open(self.tpl_file)
        tsmap[0].data = num.zeros(tsmap[0].data.shape, dtype=num.float)
        for subdir in self.subdirs:
            result_file = os.path.join(subdir, 'ts_results.dat')
            try:
                ii, jj, ra, dec, ts_vals = read_data(result_file)
            except:
                continue
            for i, j, ts in zip(ii, jj, ts_vals):
                tsmap[0].data[j][i] = ts
        tsmap.writeto(self.pars['outfile'], clobber=True)
                
    def remove_tempfiles(self):

        for subdir in self.subdirs:
            os.remove(subdir+"/par.pck")
            os.remove(subdir+"/pixel.pck")
            os.remove(subdir+"/ts_results.dat")
            os.removedirs(subdir)
        os.remove(self.tpl_file)


def gttsmap_mp(pars,num_queues,savetmp):

    tsmap = BatchTsMap(pars,num_queues,savetmp=savetmp)
    tsmap.prepareSubdirs()
    
    SQ = [(subdir,tsmap.pars,tsmap.getPixels(int(subdir)),tsmap.tpl_file) for subdir in tsmap.subdirs]
    pool = Pool(processes=tsmap.njobs)
    pool.map(launchJobs,SQ)
    
    tsmap.merge_results()
    if not savetmp:
        print "Deleting temporary files."
        tsmap.remove_tempfiles()


def cli():

    helpString = "Generates a TS Map by running seperate pixels on seperate threads.\
                  It creates a template counts map to determine the location of the \
                  pixels and the calculates the TS of a test source at each pixel on \
                  that map.  It then merges the results at the end.  The map is divided\
                  into seperate regions (called 000,001,002...) depending on the number\
                  of jobs the user requests.  It creates subdirectories for each region\
                  and operates on them within the subdirectory.  For more details on\
                  the parameters see the gttsmap help file.  NOTE:  ONLY DOES AN \
                  UNBINNED ANALYSIS.  NOTE2:  Any files referenced in the model XML file\
                  must be referenced by abosolute and not relative directories \
                  (ie. not ./ or ../)"

    parser = argparse.ArgumentParser(description=helpString)
    parser.add_argument("nxpix", type=int, help="Number of pixels along x-axis.  See gttsmap help for more information.")
    parser.add_argument("nypix", type=int, help="Number of pixels along y-axis.  See gttsmap help for more information.")
    parser.add_argument("jobs", type=int, help="The number of concurrent jobs.")
    parser.add_argument("evfile", help="Input event file.  See gttsmap help for more information.")
    parser.add_argument("scfile", help="The spacecraft data file. See gttsmap help for more information.")
    #parser.add_argument("statistic", help="UNBINNED or BINNED. See gttsmap help for more information.")
    parser.add_argument("expmap", help="Input exposure map.  See gttsmap help for more information.")    
    parser.add_argument("expcube", help="Input livetime cube.  See gttsmap help for more information.")
    parser.add_argument("srcmdl", help="XML source model definition.  Any files in the xml (like the diffuse models) need to be referenced by absolute directories. See gttsmap help for more information.")
    parser.add_argument("IRFS", help="IRFs to use.  See gttsmap help for more information.")
    parser.add_argument("optimizer", help="The optimizer (e.g. NEWMINUIT). See gttsmap help for more information.")
    parser.add_argument("ftol", type=float, help="Fit tolerance. See gttsmap help for more information.")
    parser.add_argument("toltype", type=int, help="Tolerance type (0 for RELATIVE and 1 for ABSOLUTE). See gttsmap help for more information.")
    parser.add_argument("binsz", type=float, help="Image scale (deg/pix).  See gttsmap help for more information.")
    parser.add_argument("coordsys", help="CEL or GAL.  See gttsmap help for more information.")
    parser.add_argument("xref", type=float, help="x-coord of center (RA or l).  See gttsmap help for more information.")
    parser.add_argument("yref", type=float, help="y-coord of center (DEC or b).  See gttsmap help for more information.")
    parser.add_argument("proj", help="Coordinate projection. See gttsmap help for more information.")
    parser.add_argument("outfile", help="Output file name.")

    parser.add_argument("--savetmp", default = False, help="Save the temporary files (default is False).")
    
    args = parser.parse_args()

    pars = {}

    pars['evfile'] = args.evfile
    pars['scfile'] = args.scfile
    pars['nxpix'] = args.nxpix
    pars['nypix'] = args.nypix
    pars['binsz'] = args.binsz
    pars['coordsys'] = args.coordsys
    pars['xref'] = args.xref
    pars['yref'] = args.yref
    pars['proj'] = args.proj
    pars['expmap'] = args.expmap
    pars['expcube'] = args.expcube
    pars['srcmdl'] = args.srcmdl
    pars['outfile'] = args.outfile
    pars['irfs'] = args.IRFS
    pars['optimizer'] = args.optimizer
    pars['ftol'] = args.ftol
    pars['toltype'] = args.toltype

    gttsmap_mp(pars,num_queues=args.jobs,savetmp=args.savetmp)

def cli_runLike():

    helpString = "This is a helper function that runs each individual partition.\
                  Don't use it manually."

    parser = argparse.ArgumentParser(description=helpString)
    parser.add_argument("runLike", help="Flag to indicate that you are running on a partition.")
    parser.add_argument("subdir", help="Subdirectory to run under.")
    parser.add_argument("tpl_file", help="File name of the template CMAP.")

    args = parser.parse_args()

    runLikelihood(args.subdir, "../"+args.tpl_file)



if __name__ == '__main__':

    if len(sys.argv) > 1:
        if sys.argv[1] == 'runLike':
            cli_runLike()
        else:
            cli()
    else:
        cli()

