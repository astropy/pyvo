# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Global image discovery.

This module is intended to cover the much-requested use case "give me all
images with properties x, y, and z, where these properties for now is the
location in space, time, and spectrum; sensitivity clearly would be great,
but that needs standard work.

The code here looks for data in SIA1, SIA2, and Obscore services for now.
"""

from enum import IntEnum
from typing import List, Optional, Set, Tuple, TYPE_CHECKING

from astropy import units as u
from astropy.coordinates import SkyCoord

from ..dal.sia2 import ObsCoreRecord
from .. import registry


# imports for type hints
from astropy.units.quantity import Quantity
from ..registry.regtap import RegistryResults, RegistryResource
from ..dal.sia import SIARecord


def _clean_for(records: RegistryResults, to_remove: Set[str]):
    """ cleans records with ivoids in to_remove from records.

    This modified records in place.
    """
    indexes_to_remove = []
    for index, rec in enumerate(records):
        if rec["ivoid"] in to_remove:
            indexes_to_remove.append(index)

    # I'm not happy about in-place modifications using a private attribute,
    # either, but it seems constructing DALResults on the fly is
    # really painful, too.

    # TODO: Oh dang... who do I take out rows for the _votable?
    records._votable.resources[0].tables[0].remove_rows(indexes_to_remove)


def sia1_to_obscore(sia1_result: SIARecord) -> ObsCoreRecord:
    """returns an obscore record filled from SIA1 metadata.

    This probably is a bad idea given the way ObsCoreRecord is done;
    we probably need to do per-service mapping.
    """
    raise NotImplementedError("We need a SIA1 -> Obscore mapping")


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
        self.result: List[ObsCoreRecord] = []
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

        self.sia1_recs = registry.search(
            registry.Servicetype("sia"), *constraints)
        self.sia2_recs = registry.search(
            registry.Servicetype("sia2"), *constraints)
        self.obscore_recs = registry.search(
            registry.Datamodel("obscore"), *constraints)

        # Now remove resources presumably operating on the same underlying
        # data collection.  First, we deselect by ivoid, where a more powerful
        # interface is available
        def ids(recs):
            return set(r.ivoid for r in recs)

        _clean_for(self.sia1_recs,
                ids(self.sia2_recs)|ids(self.obscore_recs))
        _clean_for(self.sia2_recs, ids(self.obscore_recs))

        # TODO: use futher heuristics to further cut down on dupes:
        # Use relationships.  I think we should tell people to use
        # IsDerivedFrom for SIA2 services built on top of TAP services.

    def _query_one_sia1(self, rec: RegistryResource):
        """runs our query against a SIA1 capability of rec.

        Since SIA1 cannot do spectral and temporal constraints itself,
        we do them client-side provided sufficient metadata is present.
        If metadata is missing, we keep or discard accoding to
        self.inclusive.
        """
        svc = rec.get_service("sia")
        for res in svc.search(pos=self.center, size=self.radius,
                intersect='overlaps'):
            new_rec = sia1_to_obscore(res)

            if not inclusive and self.spectral:
                if not new_rec.em_min<self.spectral<new_rec.em_max:
                    continue
            if not inclusive and self.time:
                if not new_rec.time_min<self.time<new_rec.time_max:
                    continue

            self.results.append(new_rec)

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
                self.log.append(f"SIA1 {rec['ivoid']} skipped: {msg}")

    def _query_one_sia2(self, rec: RegistryResource):
        """runs our query against a SIA2 capability of rec.
        """
        svc = rec.get_service("sia2")
        for res in svc.search(pos=self.space, band=self.spectrum,
                time=self.time):
            self.results.append(new_rec)

    def _query_sia2(self):
        """runs the SIA2 part of our discovery.
        """
        for rec in self.sia2_recs:
            try:
                self._query_one_sia2(rec)
            except Exception as msg:
                self.log.append(f"SIA2 {rec['ivoid']} skipped: {msg}")

    def _query_one_obscore(self, rec: RegistryResource, where_clause:str):
        """runs our query against a Obscore capability of rec.
        """
        svc = rec.get_service("tap")

        for res in svc.query("select * from ivoa.obscore"+where_clause):
            self.results.append(ObsCoreRecord(res))

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
            mjd = self.time.mjd
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
        ) -> Tuple[List[ObsCoreRecord], List[str]]:
    """returns a collection of ObsCoreRecord-s matching certain constraints
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
