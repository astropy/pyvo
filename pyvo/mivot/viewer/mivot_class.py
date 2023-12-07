# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotClass keep as an attribute dictionary __dict__ all XML objects.
"""
import numpy
from astropy import time

from pyvo.mivot.utils.vocabulary import unit_mapping
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class MivotClass:
    """
    MIVOT class is a dictionary (__dict__) with only essential information of the ModelViewerLevel3._dict.
    The dictionary keeps the hierarchy of the XML :
    "key" : {not a leaf} means key is the dmtype of an INSTANCE
    "key" : {leaf}       means key is the dmrole of an ATTRIBUTE
    "key" : "value"      means key is an element of ATTRIBUTE
    "key" : []           means key is the dmtype of a COLLECTION
    """

    def __init__(self, **kwargs):
        """
        Constructor of the MIVOT class.

        Parameters
        ----------
        kwargs : dict
            Dictionary of the XML object.
        """
        self._create_mivot_class(**kwargs)

    @property
    def epoch_propagation(self):
        """
        Property to get the EpochPropagation object.

        Returns
        -------
        ~`pyvo.mivot.features.epoch_propagation.EpochPropagation`
            The EpochPropagation object.
        """
        # We import EpochPropagation here to avoid circular imports
        from pyvo.mivot.features.epoch_propagation import EpochPropagation
        return EpochPropagation(self)

    @property
    def sky_coordinate(self):
        """
        Property to get the SkyCoord object from the EpochPropagation object.

        Returns
        -------
        ~`astropy.coordinates.sky_coordinate.SkyCoord`
            The SkyCoord object.
        """
        return self.epoch_propagation.sky_coordinate()

    def _create_mivot_class(self, **kwargs):
        """
        Recursively initialize the MIVOT class with the dictionary of the XML object got in ModelViewerLevel3.
        For the unit of the ATTRIBUTE, we add the astropy unit or the astropy time equivalence by comparing
        the value of the unit with values in time.TIME_FORMATS.keys() which is the list of time formats.
        We do the same with the unit_mapping dictionary, which is the list of astropy units.

        Parameters
        ----------
        kwargs : dict
            Dictionary of the XML object.
        """
        for key, value in kwargs.items():
            if isinstance(value, list):  # COLLECTION
                setattr(self, self._remove_model_name(key), [])
                for item in value:
                    getattr(self, self._remove_model_name(key)).append(MivotClass(**item))

            elif isinstance(value, dict):  # INSTANCE
                if not self._is_leaf(**value):
                    setattr(self, self._remove_model_name(key, True), MivotClass(**value))
                if self._is_leaf(**value):
                    setattr(self, self._remove_model_name(key), MivotClass(**value))

            else:  # ATTRIBUTE
                if key == 'value':  # We cast the value read in the row
                    setattr(self, self._remove_model_name(key),
                            MivotClass.cast_type_value(value, getattr(self, 'dmtype')))
                else:
                    setattr(self, self._remove_model_name(key), self._remove_model_name(value))
                if key == 'unit':  # We convert the unit to astropy unit or to astropy time format if possible
                    if value in unit_mapping.keys():
                        setattr(self, "astropy_unit", unit_mapping[value])
                    elif value in time.TIME_FORMATS.keys():
                        setattr(self, "astropy_unit_time", value)

    def update_mivot_class(self, row, ref=None):
        """
        Update the MIVOT class with the new data row.
        For each leaf of the MIVOT class, we update the value with the new data row, comparing the reference.

        Parameters
        ----------
        row : dict
            The new data row.
        ref : str, optional
            The reference of the data row, default is None.
        """
        for key, value in vars(self).items():
            if isinstance(value, list):
                for item in value:
                    item.update_mivot_class(row=row)
            elif isinstance(value, MivotClass):
                if isinstance(vars(value), dict):
                    if 'value' not in vars(value):
                        value.update_mivot_class(row=row)
                    if 'value' in vars(value):
                        value.update_mivot_class(row=row, ref=getattr(value, 'ref'))
            else:
                if key == 'value':
                    if ref is not None and ref != 'null':
                        print(type(row[ref]), row[ref])
                        setattr(self, self._remove_model_name(key),
                                MivotClass.cast_type_value(row[ref], getattr(self, 'dmtype')))

    def _remove_model_name(self, value, role_instance=False):
        """
        Remove the model name before each colon ":" as well as the type of the object before each point ".".
        If it is an INSTANCE of INSTANCEs, the dmrole represented as the key needs to keep his type object.
        In this case (`role_instance=True`), we just replace the point "." With an underscore "_".

        Parameters
        ----------
        value : str
            The string to process.
        role_instance : bool, optional
            If True, keeps the type object for dmroles representing an INSTANCE of INSTANCEs.
            Default is False.
        """
        if isinstance(value, str):
            # We first find the model_name before the colon
            index_underscore = value.find(":")
            if index_underscore != -1:
                # Then we find the object type before the point
                next_index_underscore = value.find(".", index_underscore + 1)

                if next_index_underscore != -1 and role_instance is False:
                    value_after_underscore = value[next_index_underscore + 1:]
                else:
                    value_after_underscore = (value[index_underscore + 1:]
                                              .replace(':', '_').replace('.', '_'))
                return value_after_underscore

            return value  # Returns unmodified string if "_" wasn't found
        else:
            return value

    @staticmethod
    def cast_type_value(value, dmtype):
        """
        Cast the value of an ATTRIBUTE based on its dmtype.
        As the type of ATTRIBUTE values returned in the dictionary is string by default,
        this function is used to cast them based on their dmtype.

        Parameters
        ----------
        value : str
            The value of the ATTRIBUTE.
        dmtype : str
            The dmtype of the ATTRIBUTE.

        Returns
        -------
        Union[bool, float, str, None]
            The cast value based on the dmtype.
        """
        if type(value) is numpy.float32 or type(value) is numpy.float64:
            return value
        lower_dmtype = dmtype.lower()
        if type(value) is str:
            lower_value = value.lower()
        else:
            lower_value = value

        if "bool" in lower_dmtype:
            if value == "1" or lower_value == "true" or lower_value is True:
                return True
            else:
                return False
        elif lower_value in ('notset', 'noset', 'null', 'none', 'nan') or value is None:
            return None
        elif (isinstance(value, numpy.ndarray) or isinstance(value, numpy.ma.core.MaskedConstant)
              or value == '--'):
            return None
        elif "real" in lower_dmtype or "double" in lower_dmtype or "float" in lower_dmtype:
            return float(value)
        else:
            return value

    def _is_leaf(self, **kwargs):
        """
        Check if the dictionary is an ATTRIBUTE.

        Parameters
        ----------
        **kwargs : dict
            The dictionary to check.

        Returns
        -------
        bool
            True if the dictionary is an ATTRIBUTE, False otherwise.
        """
        if isinstance(kwargs, dict):
            for key, value in kwargs.items():
                if isinstance(value, dict):
                    return False
        return True

    def display_class_dict(self, obj, classkey=None):
        """
        Recursively displays a serializable dictionary.
        This function is only used for debugging purposes.

        Parameters
        ----------
        obj : dict or object
            The dictionary or object to display.
        classkey : str, optional
            The key to use for the object's class name in the dictionary, default is None.

        Returns
        -------
        dict or object
            The serializable dictionary representation of the input.
        """
        if isinstance(obj, dict):
            data = {}
            for (k, v) in obj.items():
                data[k] = self.display_class_dict(v, classkey)
            return data
        elif hasattr(obj, "_ast"):
            return self.display_class_dict(obj._ast())
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [self.display_class_dict(v, classkey) for v in obj]
        elif hasattr(obj, "__dict__"):
            data = dict([(key, self.display_class_dict(value, classkey))
                         for key, value in obj.__dict__.items()
                         if not callable(value) and not key.startswith('_')])
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data
        else:
            return obj
