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
from astropy.coordinates import SkyCoord

from ..dam import obscore
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
                "bandpass_hilimit": rec.em_max.to(u.m).value,
                "bandpass_lolimit": rec.em_min.to(u.m).value,
                # Sigh.  Try to guess exposure time?
                "t_min": rec.dateobs,
                "t_max": rec.dateobs,
                "access_estsize": rec.filesize/1024,
                "access_format": rec.format,
                "instrument_name": rec.instr,
                "s_xsel1": rec.naxis[0],
                "s_xsel2": rec.naxis[1],
                "s_ra": rec.pos[0],
                "s_dec": rec.pos[1],
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

    For now, we expose several methods to be called in succession
    (see discover_images); that's because we *may* want to make
    this API after all and admit user manipulation of our state
    in between the larger steps.

    See discover_images for a discussion of its constructor parameters.
    """
    def __init__(self, space, spectrum, time, inclusive):
        self.space, self.spectrum, self.time = space, spectrum, time
        if self.space:
            self.center = SkyCoord(self.space[0], self.space[1], unit='deg')
            self.radius = self.space[2]*u.deg

        self.inclusive = inclusive
        self.result: List[obscore.ObsCoreMetadata] = []
        self.log: List[str] = []

    def collect_services(self):
        """fills the X_recs attributes with resources declaring coverage
        for our constraints.

        X at this point is sia1, sia2, and obscore.

        It tries to filter out as many duplicates (i.e., services operating on
        the same data collections) as it can.  The order of preference is
        Obscore, SIA2, SIA.
        """
        constraints = []
        if self.space:
            constraints.append(
                registry.Spatial(self.space, inclusive=self.inclusive))
        if self.spectrum:
            constraints.append(
                registry.Spectral(self.spectrum, inclusive=self.inclusive))
        if self.time:
            constraints.append(
                registry.Temporal(self.time, inclusive=self.inclusive))

        self.sia1_recs = [Queriable(r) for r in registry.search(
            registry.Servicetype("sia"), *constraints)]
        self.sia2_recs = [Queriable(r) for r in registry.search(
            registry.Servicetype("sia2"), *constraints)]
        self.obscore_recs = [Queriable(r) for r in registry.search(
            registry.Datamodel("obscore"), *constraints)]

        # Now remove resources presumably operating on the same underlying
        # data collection.  First, we deselect by ivoid, where a more powerful
        # interface is available
        def ids(recs):
            return set(r.ivoid for r in recs)

        self.sia1_recs = _clean_for(self.sia1_recs,
                ids(self.sia2_recs)|ids(self.obscore_recs))
        self.sia2_recs = _clean_for(self.sia2_recs, ids(self.obscore_recs))

        # TODO: use futher heuristics to further cut down on dupes:
        # Use relationships.  I think we should tell people to use
        # IsDerivedFrom for SIA2 services built on top of TAP services.

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
                if not self.time-1<sia1_rec.dateobs<self.time+1:
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
        if self.space is None:
            self.log.append("SIA1 servies skipped do to missing space"
                " constraint")
            return

        for rec in self.sia1_recs:
            try:
                self._query_one_sia1(rec)
            except Exception as msg:
                self.log.append(f"SIA1 {rec.ivoid} skipped: {msg}")

    def _query_one_sia2(self, rec: Queriable):
        """runs our query against a SIA2 capability of rec.
        """
        svc = rec.res_rec.get_service("sia2")
        self.results.extend(
            ImageFound.from_obscore_recs(
                svc.search(pos=self.space, band=self.spectrum, time=self.time)))

    def _query_sia2(self):
        """runs the SIA2 part of our discovery.
        """
        for rec in self.sia2_recs:
            try:
                self._query_one_sia2(rec)
            except Exception as msg:
                self.log.append(f"SIA2 {rec.ivoid} skipped: {msg}")

    def _query_one_obscore(self, rec: Queriable, where_clause:str):
        """runs our query against a Obscore capability of rec.
        """
        svc = rec.res_rec.get_service("tap")
        self.results.extend(
            ImageFound.from_obscore_recs(
                svc.query("select * from ivoa.obscore"+where_clause)))

    def _query_obscore(self):
        """runs the Obscore part of our discovery.
        """
        # TODO: we probably should make the dataproduct type constraint
        # configurable.
        where_parts = ["dataproduct_type='image'"]
        # TODO: we'd need extra logic for inclusive here, too
        if self.space:
            where_parts.append("distance(s_ra, s_dec, {}, {}) < {}".format(
                *self.space))
        if self.spectrum:
            meters = self.spectrum.to(u.m, equivalancies=u.spectral()).value
            where_parts.append(f"(em_min<={meters} AND em_max>={meters})")
        if self.time:
            mjd = self.time.mjd.value
            where_parts.append(f"(t_min<={mjd} AND t_max>={mjd})")

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
        self._query_sia1()
        self._query_sia2()
        self._query_obscore()


def discover_images(
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
    discoverer.collect_services()
    discoverer.query_services()
    # TODO: We should un-dupe by image access URL
    # TODO: We could compute SODA cutout URLs here in addition.
    return discoverer.result, discoverer.log
