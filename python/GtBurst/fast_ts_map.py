from UnbinnedAnalysis import *
import astropy.wcs as pywcs
import pyLikelihood

from astropy.coordinates.angle_utilities import angular_separation
import numpy as np


class FastTSMap(object):

    def __init__(self, pylike_object, target="GRB"):
        """

        :param pylike_object: a UnbinnedAnalysis.UnbinnedAnalysis object containing a source in the center
        """

        self._pylike_object = pylike_object

        logLike = self._pylike_object.logLike

        # Remove target source (will be replaced with the test source)
        self._target_source = logLike.deleteSource(target)

        ra = self._pylike_object.model[target]['Position']['RA']
        dec = self._pylike_object.model[target]['Position']['DEC']

        # Generate a test source (and compute the exposure, since we provide the observation in the constructor)
        self._test_source = pyLikelihood.PointSource(ra, dec, logLike.observation())
        self._test_source.setSpectrum(self._target_source.spectrum())
        self._test_source.setName("_test_source")

        # compute the value for the likelihood without the point source
        logLike0 = logLike.value()

        # Optimize (i.e., fit) the model without the point source
        self._pylike_object.optimize(verbosity=0)
        logLike0 = max(logLike.value(), logLike0)

        # Store it
        self._logLike0 = float(logLike0)

        # Save the values for the free parameters in the model without the point source
        self._nullhyp_best_fit_param = pyLikelihood.DoubleVector()
        # This is a C++ call-by-reference, so self._nullhyp_best_fit_param will be changed
        logLike.getFreeParamValues(self._nullhyp_best_fit_param)

    def search_for_maximum(self, ra_center, dec_center, half_side_deg, n_side, proj_name='AIT', verbose=False):
        """

        :param ra_center: R.A. of the center of the map
        :param dec_center: Dec of the center of the map
        :param half_size_deg: half size of the side of the TS map ("radius", even though it is a square)
        :param n_side: number of points on one side. So n_side = 5 means that a 5x5 map will be computed
        :param stepsize: size of the step, i.e., distance between two adiancent points in the RA or Dec direction
        :param proj_name: name for the projection (default: AIT). All projections supported by astropy.wcs can be used
        :return: (max_ts_position, max_ts): returns a tuple of (RA, Dec) and the maximum TS found
        """

        # Figure out step size
        stepsize = half_side_deg / (n_side / 2.0)

        # Create WCS object which will allow us to make the grid

        wcs = pywcs.WCS(naxis=2)
        wcs.wcs.crpix = [n_side / 2. + 0.5, n_side / 2. + 0.5]
        wcs.wcs.cdelt = [-stepsize, stepsize]
        wcs.wcs.crval = [float(ra_center), float(dec_center)]
        wcs.wcs.ctype = ["RA---%s" % proj_name, "DEC--%s" % proj_name]

        # Compute all TSs

        # These two will hold maximum and position of the maximum
        # Init them with worse case scenario
        max_ts = 0.0
        max_ts_position = (ra_center, dec_center)
        ang_sep = []

        for i in range(n_side):

            for j in range(n_side):

                this_ra, this_dec = wcs.wcs_pix2world(i, j, 0)

                this_TS = self._calc_one_TS(float(this_ra), float(this_dec))

                if this_TS >= max_ts:

                    # New maximum
                    max_ts = this_TS
                    max_ts_position = (this_ra, this_dec)

                if verbose:

                    ang_sep.append(np.rad2deg(angular_separation(*np.deg2rad([ra_center, dec_center,
                                                                              this_ra, this_dec]))))

                    print("(%.3f, %.3f) -> %.2f (%.3f deg away from center)" % (this_ra, this_dec,
                                                                                this_TS, ang_sep[-1]))

        if verbose:
            print("Total number of points: %i" % len(ang_sep))
            print("Minimum ang. dist: %s deg" % min(ang_sep))
            print("Maximum ang. dist: %s deg" % max(ang_sep))

        # Find maximum and its position
        return max_ts_position, max_ts

    def _calc_one_TS(self, ra, dec):

        logLike = self._pylike_object.logLike

        # The first False says not to recompute the exposure, the second one avoid verbosity
        self._test_source.setDir(ra, dec, False, False)
        logLike.addSource(self._test_source)

        # This is the fastest way to minimize -logL if we don't care about errors

        self._pylike_object.optObject.find_min_only(0, 1e-5)

        logLike1 = logLike.value()
        TS = 2.0 * (logLike1 - self._logLike0)
        logLike.deleteSource("_test_source")

        # Restore the parameters of the model without the source to their best fit
        # values
        logLike.setFreeParamValues(self._nullhyp_best_fit_param)

        return TS
