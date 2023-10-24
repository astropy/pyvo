# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Global image discovery.

This module is intended to cover the much-requested use case "give me all
images with properties x, y, and z, where these properties for now is the
location in space, time, and spectrum; sensitivity clearly would be great,
but that needs standard work.

The code here looks for data in SIA1, SIA2, and Obscore services for now.
"""

import functools

from astropy import units as u
from astropy import time
from astropy.coordinates import SkyCoord

from ..dam import obscore
from .. import dal
from .. import registry


# imports for type hints
from typing import List, Optional, Set, Tuple
from astropy.units.quantity import Quantity


class Queriable:
    """A facade for a queriable service.

    We keep these rather than work on
    `pyvo.registry.regtap.RegistryResource`-s directly because the latter
    actually live in VOTables which are very hard to manipulate.

    They are constructed with a resource record.
    """
    def __init__(self, res_rec):
        self.res_rec = res_rec
        self.ivoid = res_rec.ivoid

    def __str__(self):
        return f"<{self.ivoid}>"


@functools.cache
def obscore_column_names():
    """returns the names of obscore columns.

    For lack of alternatives, I pull them out of ObsCoreMetadata for now.
    """
    return [name for name in dir(obscore.ObsCoreMetadata())
        if not name.startswith("_")]


class ImageFound(obscore.ObsCoreMetadata):
    """Obscore metadata for a found record.

    We're pulling these out from the various VOTables that we
    retrieve because we need to do some manipulation of them
    that's simpler to do if they are proper Python objects.

    This is an implementation detail, though; eventually, we're
    turning these into an astropy table and further into a VOTable
    to make this as compatible with the DAL services as possible.
    """
    attr_names = set(obscore_column_names())

    def __init__(self, obscore_record):
        for k, v in obscore_record.items():
            if k not in self.attr_names:
                raise TypeError(
                    f"ImageFound does not accept {k} keys")
            setattr(self, k, v)

    @classmethod
    def from_obscore_recs(cls, obscore_result):
        ap_table = obscore_result.to_table()
        our_keys = [n for n in ap_table.colnames if n in cls.attr_names]
        for row in obscore_result:
            yield cls(dict(zip(our_keys, (row[n] for n in our_keys))))

    @classmethod
    def from_sia1_recs(cls, sia1_result, filter_func):
        for rec in sia1_result:
            if not filter_func(rec):
                continue
            mapped = {
                "dataproduct_type": "image" if rec.naxes == 2 else "cube",
                "access_url": rec.acref,
                "em_max": rec.bandpass_hilimit is not None
                    and rec.bandpass_hilimit.to(u.m).value,
                "em_min": rec.bandpass_lolimit is not None
                    and rec.bandpass_lolimit.to(u.m).value,
                # Sigh.  Try to guess exposure time?
                "t_min": rec.dateobs.mjd,
                "t_max": rec.dateobs.mjd,
                "access_estsize": rec.filesize/1024,
                "access_format": rec.format,
                "instrument_name": rec.instr,
                "s_xel1": rec.naxis[0].to(u.pix).value,
                "s_xel2": rec.naxis[1].to(u.pix).value,
                "s_ra": rec.pos.icrs.ra.to(u.deg).value,
                "s_dec": rec.pos.icrs.dec.to(u.deg).value,
                "obs_title": rec.title,
                # TODO: do more (s_resgion!) on the basis of the WCS parts
            }
            yield cls(mapped)


def _clean_for(records: List[Queriable], ivoids_to_remove: Set[str]):
    """returns the Queriables in records the ivoids of which are
    not in ivoids_to_remove.
    """
    return [r for r in records if r.ivoid not in ivoids_to_remove]


class _ImageDiscoverer:
    """A management class for VO global image discovery.

    This encapsulates all of constraints, service lists, results, and
    diagnostics.  This probably should not be considered API but
    rather as an implementation detail of discover_images.

    The normal usage is do call discover_services(), which will locate
    all VO services that may have relevant data.  Alternatively, call
    set_services(registry_results) with some result of a registry.search()
    call.  _ImageDiscoverer will then pick capabilities it can use out
    of the resource records.  Records without usable capabilities are
    silently ignored.

    Then call query_services to execute the discovery query on these
    services.

    See images_globally for a discussion of its constructor parameters.
    """
    # Constraint defaults
    # a float in metres
    spectrum = None
    # an MJD float
    time = None
    # a center as a 2-tuple in ICRS degrees
    center = None
    # a radius as a float in degrees
    radius = None

    def __init__(self,
            space=None, spectrum=None, time=None, inclusive=False):
        if space:
            self.center = (space[0], space[1])
            self.radius = space[2]

        if spectrum is not None:
            self.spectrum = spectrum.to(u.m, equivalencies=u.spectral()).value
        # a float in MJD
        if time is not None:
            self.time = time.mjd

        self.inclusive = inclusive
        self.results: List[obscore.ObsCoreMetadata] = []
        self.log: List[str] = []
        self.sia1_recs, self.sia2_recs, self.obscore_recs = [], [], []

    def _purge_redundant_services(self):
        """removes services querying data already covered by more capable
        services from our current services lists.
        """
        def ids(recs):
            return set(r.ivoid for r in recs)

        self.sia1_recs = _clean_for(self.sia1_recs,
                ids(self.sia2_recs)|ids(self.obscore_recs))
        self.sia2_recs = _clean_for(self.sia2_recs, ids(self.obscore_recs))

        # TODO: use futher heuristics to further cut down on dupes:
        # Use relationships.  I think we should tell people to use
        # IsServiceFor for (say) SIA2 services built on top of TAP services.

    def discover_services(self):
        """fills the X_recs attributes with resources declaring coverage
        for our constraints.

        X at this point is sia1, sia2, and obscore.

        It tries to filter out as many duplicates (i.e., services operating on
        the same data collections) as it can.  The order of preference is
        Obscore, SIA2, SIA.
        """
        constraints = []
        if self.center is not None:
            constraints.append(
                registry.Spatial(list(self.center)+[self.radius],
                    inclusive=self.inclusive))
        if self.spectrum is not None:
            constraints.append(
                registry.Spectral(self.spectrum*u.m,
                    inclusive=self.inclusive))
        if self.time is not None:
            constraints.append(
                registry.Temporal(self.time, inclusive=self.inclusive))

        self.sia1_recs = [Queriable(r) for r in registry.search(
            registry.Servicetype("sia"), *constraints)]
        self.sia2_recs = [Queriable(r) for r in registry.search(
            registry.Servicetype("sia2"), *constraints)]
        self.obscore_recs = [Queriable(r) for r in registry.search(
            registry.Datamodel("obscore"), *constraints)]

        self._purge_redundant_services()

    def set_services(self,
            registry_results: registry.RegistryResults) -> None:
        """as an alternative to discover_services, this sets the services
        to be queried to the result of a custom registry query.

        This will pick the "most capabable" interface from each record
        and ignore records without image discovery capabilities.
        """
        for rsc in registry_results:
            if "tap" in rsc.access_modes():
                # TODO: we ought to ensure there's an obscore
                # table on this; but then: let's rather fix obscore
                # discovery
                self.obscore_recs.append(Queriable(rsc))
            elif "sia2" in rsc.access_modes():
                self.sia2_recs.append(Queriable(rsc))
            elif "sia" in rsc.access_modes():
                self.sia1_recs.append(Queriable(rsc))
            # else ignore this record

    def _query_one_sia1(self, rec: Queriable):
        """runs our query against a SIA1 capability of rec.

        Since SIA1 cannot do spectral and temporal constraints itself,
        we do them client-side provided sufficient metadata is present.
        If metadata is missing, we keep or discard accoding to
        self.inclusive.
        """
        def non_spatial_filter(sia1_rec):
            if self.spectrum and not self.inclusive and (
                    sia1_rec.bandpass_hilmit and sia1_rec.bandpass_lolimit):
                if not (sia1_rec.bandpass_lolimit
                        <= self.spectrum
                        <= sia1_rec.bandpass_hilimit):
                    return False

            # Regrettably, the exposure time is not part of SIA1 standard
            # metadata.  TODO: require time to be an interval and
            # then replace check for dateobs to be within that interval.
            if self.time and not self.inclusive and sia1_rec.dateobs:
                if not self.time-1<sia1_rec.dateobs.mjd<self.time+1:
                    return False
            return True

        svc = rec.res_rec.get_service("sia")
        self.results.extend(
            ImageFound.from_sia1_recs(
                svc.search(
                    pos=self.center, size=self.radius, intersect='overlaps'),
                non_spatial_filter))

    def _query_sia1(self):
        """runs the SIA1 part of our discovery.

        This will be a no-op without a space constraint due to
        limitations of SIA1.
        """
        if self.center is None:
            self.log.append("SIA1 service skipped do to missing space"
                " constraint")
            return

        for rec in self.sia1_recs:
            try:
                self._query_one_sia1(rec)
            except Exception as msg:
                self.log.append(f"SIA1 {rec.ivoid} skipped: {msg}")
                raise

    def _query_one_sia2(self, rec: Queriable):
        """runs our query against a SIA2 capability of rec.
        """
        svc = rec.res_rec.get_service("sia2")
        constraints = {}
        if self.center is not None:
            constraints["pos"] = self.center+(self.radius,)
        if self.spectrum is not None:
            constraints["band"] = self.spectrum
        if self.time is not None:
            constraints["time"] = time.Time(self.time, format="mjd")

        matches = list(
            ImageFound.from_obscore_recs(svc.search(**constraints)))
        if len(matches):
            self.log.append(f"SIA2 service {rec}: {len(matches)} recs")
        else:
            self.log.append(f"SIA2 service {rec}: no matches")

        self.results.extend(matches)

    def _query_sia2(self):
        """runs the SIA2 part of our discovery.
        """
        for rec in self.sia2_recs:
            try:
                self._query_one_sia2(rec)
            except Exception as msg:
                self.log.append(f"SIA2 {rec.ivoid} skipped: {msg}")
                raise

    def _query_one_obscore(self, rec: Queriable, where_clause:str):
        """runs our query against a Obscore capability of rec.
        """
        svc = rec.res_rec.get_service("tap")
        recs = svc.query("select * from ivoa.obscore"+where_clause)
        self.results.extend(
            ImageFound.from_obscore_recs(recs))

    def _query_obscore(self):
        """runs the Obscore part of our discovery.
        """
        # TODO: we probably should make the dataproduct type constraint
        # configurable.
        where_parts = ["dataproduct_type='image'"]
        # TODO: we'd need extra logic for inclusive here, too
        if self.center is not None:
            where_parts.append("distance(s_ra, s_dec, {}, {}) < {}".format(
                self.center[0], self.center[1], self.radius))
        if self.spectrum is not None:
            where_parts.append(
                f"(em_min<={self.spectrum} AND em_max>={self.spectrum})")
        if self.time is not None:
            where_parts.append(f"(t_min<={self.time} AND t_max>={self.time})")

        where_clause = "WHERE "+(" AND ".join(where_parts))

        for rec in self.obscore_recs:
            try:
                self._query_one_obscore(rec, where_clause)
            except Exception as msg:
                self.log.append(f"Obscore {rec['ivoid']} skipped: {msg}")

    def query_services(self):
        """queries the discovered image services according to our
        constraints.

        This creates fills the results and the log attributes.
        """
        if (not self.sia1_recs
                and not self.sia2_recs
                and not self.obscore_recs):
            raise dal.DALQueryError("No services to query.  Unless"
                " you overrode service selection, you will have to"
                " loosen your constraints.")
        self._query_sia1()
        self._query_sia2()
        self._query_obscore()


def images_globally(
        space: Optional[Tuple[float, float, float]]=None,
        spectrum: Optional[Quantity]=None,
        time: Optional[float]=None,
        inclusive: bool=False
        ) -> Tuple[List[obscore.ObsCoreMetadata], List[str]]:
    """returns a collection of ObsCoreMetadata-s matching certain constraints
    and a list of log lines.

    Parameters
    ----------

    space :
        An optional tuple of ra, dec, and the search radius, all in degrees;
        images returned must intersect a spherical circle described in this
        way.
    spectrum :
        An astropy quantity convertible to a (vacuum) wavelength; images
        must cover this point in the (electromagnetic) spectrum.
    time :
        An astropy time that must be in the observation time of the image
        (if it declares a time).
    inclusive :
        Set to True to incluse services that do not declare their
        STC coverage.  By 2023, it's a good idea to do that as many
        relevant archives do not do that.

    When an image has insufficient metadata to evaluate a constraint, it
    is excluded; this mimics the behaviour of SQL engines that consider
    comparisons with NULL-s false.
    """
    discoverer = _ImageDiscoverer(space, spectrum, time, inclusive)
    discoverer.discover_services()
    discoverer.query_services()
    # TODO: We should un-dupe by image access URL
    # TODO: We could compute SODA cutout URLs here in addition.
    return discoverer.results, discoverer.log
