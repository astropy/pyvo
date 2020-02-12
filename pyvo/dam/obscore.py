# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for representing data in ObsCore format

"""

__all__ = ['ObsCore', 'POLARIZATION_STATES', 'CALIBRATION_LEVELS']


# to be moved to ObsCore
POLARIZATION_STATES = ['I', 'Q', 'U', 'V', 'RR', 'LL', 'RL', 'LR',
                       'XX', 'YY', 'XY', 'YX', 'POLI', 'POLA']
CALIBRATION_LEVELS = [0, 1, 2, 3, 4]


class ObsCore():
    """
    Representation of an ObsCore observation

    TBD setters to do validation and unit check
    """
    def __init__(self):

        ###          OBSERVATION INFO
        self.dataproduct_type = None
        self.dataproduct_subtype = None
        self.calib_level = None

        ###          TARGET INFO
        self.target_name = None
        self.target_class = None

        ###          DATA DESCRIPTION
        self.id = None
        self.title = None
        self.collection = None
        self.create_date = None
        self.creator_name = None
        self.creator_did = None

        ##         CURATION INFORMATION
        self.release_date = None
        self.obs_publisher_id = None
        self.publisher_id = None
        self.bib_reference = None
        self.data_rights = None

        ##           ACCESS INFORMATION
        self.access_url = None
        self.access_format = None
        self.access_estsize = None

        ##           SPATIAL CHARACTERISATION
        self.pos = None
        self.radius = None
        self.region = None
        self.spatial_resolution = None
        self.spatial_xel = None
        self.spatial_ucd = None
        self.spatial_unit = None
        self.resolution_min = None
        self.resolution_max = None
        self.spatial_calib_status = None
        self.spatial_stat_error = None
        self.pixel_scale = None

        ##           TIME CHARACTERISATION
        self.time_xel = None
        self.ref_pos = None
        self.time_bounds = None
        self.exptime = None
        self.time_resolution = None
        self.time_calib_status = None
        self.time_stat_error = None

        ##           SPECTRAL CHARACTERISATION
        self.spectral_xel = None
        self.spectral_ucd = None
        self.spectral_unit = None
        self.spectral_calib_status = None
        self.spectral_bounds = None
        self.resolving_power = None
        self.resolving_power_min = None
        self.resolving_power_max = None
        self.spectral_resolution = None
        self.spectral_stat_error = None

        ##           OBSERVABLE AXIS
        self.obs_ucd = None
        self.obs_unit = None
        self.obs_calib_status = None
        self.obs_stat_error = None

        ##           POLARIZATION CHARACTERISATION
        self.pol_xel = None
        self.states = None

        ##           PROVENANCE
        self.instrument = None
        self.facility = None
        self.proposal_id = None
