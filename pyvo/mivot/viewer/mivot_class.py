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
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.__dict__[self.remove_model_name(key)] = []
                for item in value:
                    self.__dict__[self.remove_model_name(key)].append(MivotClass(**item))

            elif isinstance(value, dict) and 'value' not in value:
                self.__dict__[self.remove_model_name(key, True)] = MivotClass(**value)

            else:
                if isinstance(value, dict) and self.is_leaf(**value):
                    self.__dict__[self.remove_model_name(key)] = MivotClass(**value)

                else:
                    self.__dict__[self.remove_model_name(key)] = self.remove_model_name(value)

    def remove_model_name(self, value, role_instance=False):
        """
        Remove the model name before each colon ":" as well as the type of the object before each point "."
        If it is an INSTANCE of INSTANCEs, the dmrole represented as the key needs to keep his type object,
        in this case ("role_instance=True"), we just replace the point "." With an underscore "_".
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
                    value_after_underscore = value[index_underscore + 1:].replace(':', '_').replace('.', '_')
                return value_after_underscore

            return value  # Returns unmodified string if "_" wasn't found
        else:
            return value

    def is_leaf(self, **kwargs):
        """
        Used to check if the dictionary is an ATTRIBUTE
        """
        if isinstance(kwargs, dict):
            for key, value in kwargs.items():
                if isinstance(value, dict):
                    return False
        return True

    def display_class_dict(self, obj, classkey=None):
        """
        Used to show a serializable dictionary
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
