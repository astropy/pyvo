# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotClass keep as an attribute dictionary __dict__ all XML objects.
"""
from astropy.time import Time

from pyvo.mivot.features.epoch_propagation import EpochPropagation
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class MivotClass:
    """
    MIVOT class is a dictionary (__dict__) with only essential information of the ModelViewerLayer3._dict.
    The dictionary keeps the hierarchy of the XML :
    "key" : {not a leaf} means key is the dmtype of an INSTANCE
    "key" : {leaf}       means key is the dmrole of an ATTRIBUTE
    "key" : "value"      means key is an element of ATTRIBUTE
    "key" : []           means key is the dmtype of a COLLECTION
    """
    EpochPropagation = EpochPropagation("EpochPropagation")
    REFERENCE = {}

    def __init__(self, **kwargs):
        """
        Constructor of the MIVOT class.

        Parameters
        ----------
        kwargs : dict
            Dictionary of the XML object.
        """
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.__dict__[self._remove_model_name(key)] = []
                for item in value:
                    self.__dict__[self._remove_model_name(key)].append(MivotClass(**item))

            elif isinstance(value, dict) and 'value' not in value:
                self.__dict__[self._remove_model_name(key, True)] = MivotClass(**value)

            else:
                if isinstance(value, dict) and self._is_leaf(**value):
                    self.__dict__[self._remove_model_name(key)] = MivotClass(**value)
                    if self.dmtype == "EpochPosition":
                        self._fill_epoch_propagation(key.lower(), value)
                    if "frame" in key.lower() and "string" in value["dmtype"]:
                        self.EpochPropagation.REFERENCE["frame"] = value["value"].lower()
                else:
                    self.__dict__[self._remove_model_name(key)] = self._remove_model_name(value)

    def _fill_epoch_propagation(self, key_low, value):
        """
        Fill the REFERENCE dictionary of the EpochPropagation object.

        Parameters
        ----------
        key_low : str
            The key of the dictionary in lowercase.
        value : dict
            The value of the dictionary.
        """
        if ("longitude" or "ra") in key_low:
            if "pm" not in key_low and value["unit"] == "deg":
                self.EpochPropagation.REFERENCE["longitude"] = value['value']
            elif "pm" in key_low and value["unit"] == "mas/year":
                self.EpochPropagation.REFERENCE["pm_longitude"] = value['value']
        if ("latitude" or "dec") in key_low:
            if "pm" not in key_low and value["unit"] == "deg":
                self.EpochPropagation.REFERENCE["latitude"] = value['value']
            elif "pm" in key_low and value["unit"] == "mas/year":
                self.EpochPropagation.REFERENCE["pm_latitude"] = value['value']
        if ("radial" or "velocity") in key_low and value["unit"] == "km/s":
            self.EpochPropagation.REFERENCE["radial_velocity"] = value["value"]
        if "parallax" in key_low and value["unit"] == ("mas" or "pc"):
            self.EpochPropagation.REFERENCE["parallax"] = value["value"]
        if "epoch" in key_low and value["unit"] == "year":
            self.EpochPropagation.REFERENCE["epoch"] = Time(value["value"], format="decimalyear")

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
