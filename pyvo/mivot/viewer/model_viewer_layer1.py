from pyvo.mivot.utils.exceptions import *
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class ModelViewerLayer1(object):
    """
    The ModelViewerLayer1 takes an instance of the `~pyvo.mivot.viewer.model_viewer.ModelViewer` object as a parameter
    and provides multiple getters on the XML that already has references resolved by default
    with the `~pyvo.mivot.viewer.model_viewer.ModelViewer._get_model_view()` function.
    """
    def __init__(self, model_viewer):
        self.model_viewer = model_viewer
        self._xml_view = model_viewer._get_model_view()

    def get_instance_by_role(self, dmrole, all=False):
        """
        Returns the instance matching with @dmrole.
        If all=True, returns a list of all instances matching with @dmrole.
        :param dmrole: The @dmrole to look for.
        :param all: Boolean, if True, returns a list of all INSTANCEs.
        :raises MivotElementNotFound: If dmrole is not found.
        """
        if all is False:
            if self.model_viewer._get_model_view().find(f'.//INSTANCE[@dmrole="{dmrole}"]') is not None:
                for ele in self.model_viewer._get_model_view().xpath(f'.//INSTANCE[@dmrole="{dmrole}"]'):
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any instances of the VOTable")
        elif all is True:
            if self.model_viewer._get_model_view().find(f'.//INSTANCE[@dmrole="{dmrole}"]') is not None:
                ele = []
                for elem in self.model_viewer._get_model_view().xpath(f'.//INSTANCE[@dmrole="{dmrole}"]'):
                    ele.append(elem)
                if ele:
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any instances of the VOTable")
        return None

    def get_instance_by_type(self, dmtype, all=False):
        """
        Returns the instance matching with @dmtype.
        If all=True, returns a list of all instances matching with @dmtype.
        :param dmtype: The @dmtype to look for.
        :param all: Boolean, if True, returns a list of all INSTANCEs.
        :raises MivotElementNotFound: If dmtype is not found.
        """
        if all is False:
            if self.model_viewer._get_model_view().find(f'.//INSTANCE[@dmtype="{dmtype}"]') is not None:
                for ele in self.model_viewer._get_model_view().xpath(f'.//INSTANCE[@dmtype="{dmtype}"]'):
                    if ele is not None:
                        return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmtype {dmtype} in any instances of the VOTable")
        elif all is True:
            if self.model_viewer._get_model_view().find(f'.//INSTANCE[@dmtype="{dmtype}"]') is not None:
                ele = []
                for elem in self.model_viewer._get_model_view().xpath(f'.//INSTANCE[@dmtype="{dmtype}"]'):
                    ele.append(elem)
                if ele:
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmtype {dmtype} in any instances of the VOTable")
            return ele
        return None

    def get_collection_by_role(self, dmrole, all=False):
        """
        Returns the collection matching with @dmrole
        If all=True, returns a list of all instances matching with @dmtype.
        :param dmrole: The @dmrole to look for.
        :param all: Boolean, if True, returns a list of all COLLECTION.
        :raises MivotElementNotFound: If dmrole is not found
        """
        if all is False:
            if self.model_viewer._get_model_view().find(f'.//COLLECTION[@dmrole="{dmrole}"]') is not None:
                for ele in self.model_viewer._get_model_view().xpath(f'.//COLLECTION[@dmrole="{dmrole}"]'):
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any collections of the VOTable")
        elif all is True:
            if self.model_viewer._get_model_view().find(f'.//COLLECTION[@dmrole="{dmrole}"]') is not None:
                ele = []
                for elem in self.model_viewer._get_model_view().xpath(f'.//COLLECTION[@dmrole="{dmrole}"]'):
                    ele.append(elem)
                if ele:
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any collections of the VOTable")
            return ele
        return None
