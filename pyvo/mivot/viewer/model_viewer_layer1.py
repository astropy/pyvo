# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
ModelViewerLayer1 provides several getters on an XML instance.
"""
from pyvo.mivot.utils.exceptions import MivotElementNotFound
from pyvo.mivot.utils.xpath_utils import XPath
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class ModelViewerLayer1:
    """
    The ModelViewerLayer1 takes an instance of the `~pyvo.mivot.viewer.model_viewer.ModelViewer`
    object as a parameter and provides multiple getters on the XML that already has references
    resolved by default with `~pyvo.mivot.viewer.model_viewer.ModelViewer._get_model_view()`.
    """
    def __init__(self, model_viewer):
        self.model_viewer = model_viewer
        self._xml_view = model_viewer._get_model_view()

    def get_instance_by_role(self, dmrole, all=False):
        """
        Return the instance matching with @dmrole.
        If all is False, returns the first INSTANCE matching with @dmrole.
        If all is True, returns a list of all instances matching with @dmrole.

        Parameters
        ----------
        dmrole : str
            The @dmrole to look for.
        all : bool, optional
            If True, returns a list of all instances, otherwise returns the first instance.
            Default is False.

        Returns
        -------
        Union[~`xml.etree.ElementTree.Element`, List[~`xml.etree.ElementTree.Element`], None]
            If all is False, returns the instance matching with @dmrole.
            If all is True, returns a list of all instances matching with @dmrole.
            If no matching instance is found, returns None.

        Raises
        ------
        MivotElementNotFound
            If dmrole is not found.
        """
        if all is False:
            if len(XPath.x_path(self.model_viewer._get_model_view(),
                                f'.//INSTANCE[@dmrole="{dmrole}"]')) != 0:
                for ele in XPath.x_path(self.model_viewer._get_model_view(),
                                        f'.//INSTANCE[@dmrole="{dmrole}"]'):
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any instances of the VOTable")
        elif all is True:
            if len(XPath.x_path(self.model_viewer._get_model_view(),
                                f'.//INSTANCE[@dmrole="{dmrole}"]')) != 0:
                ele = []
                for elem in XPath.x_path(self.model_viewer._get_model_view(),
                                         f'.//INSTANCE[@dmrole="{dmrole}"]'):
                    ele.append(elem)
                if ele:
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any instances of the VOTable")
        return None

    def get_instance_by_type(self, dmtype, all=False):
        """
        Return the instance matching with @dmtype.

        If all is False, returns the first INSTANCE matching with @dmtype.
        If all is True, returns a list of all instances matching with @dmtype.

        Parameters
        ----------
        dmtype : str
            The @dmtype to look for.
        all : bool, optional
            If True, returns a list of all instances, otherwise returns the first instance.
            Default is False.

        Returns
        -------
        Union[~`xml.etree.ElementTree.Element`, List[~`xml.etree.ElementTree.Element`], None]
            If all is False, returns the instance matching with @dmtype.
            If all is True, returns a list of all instances matching with @dmtype.
            If no matching instance is found, returns None.

        Raises
        ------
        MivotElementNotFound
            If dmtype is not found.
        """
        if all is False:
            if len(XPath.x_path(self.model_viewer._get_model_view(),
                                f'.//INSTANCE[@dmtype="{dmtype}"]')) != 0:
                for ele in XPath.x_path(self.model_viewer._get_model_view(),
                                        f'.//INSTANCE[@dmtype="{dmtype}"]'):
                    if ele is not None:
                        return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmtype {dmtype} in any instances of the VOTable")
        elif all is True:
            if len(XPath.x_path(self.model_viewer._get_model_view(),
                                f'.//INSTANCE[@dmtype="{dmtype}"]')) != 0:
                ele = []
                for elem in XPath.x_path(self.model_viewer._get_model_view(),
                                         f'.//INSTANCE[@dmtype="{dmtype}"]'):
                    ele.append(elem)
                if ele:
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmtype {dmtype} in any instances of the VOTable")
            return ele
        return None

    def get_collection_by_role(self, dmrole, all=False):
        """
        Return the collection matching with @dmrole.
        If all is False, returns the first COLLECTION matching with @dmrole.
        If all is True, returns a list of all COLLECTION matching with @dmrole.

        Parameters
        ----------
        dmrole : str
            The @dmrole to look for.
        all : bool, optional
            If True, returns a list of all COLLECTION, otherwise returns the first COLLECTION.
            Default is False.

        Returns
        -------
        Union[~`xml.etree.ElementTree.Element`, List[~`xml.etree.ElementTree.Element`], None]
            If all is False, returns the collection matching with @dmrole.
            If all is True, returns a list of all collections matching with @dmrole.
            If no matching collection is found, returns None.

        Raises
        ------
        MivotElementNotFound
            If dmrole is not found.
        """
        if all is False:
            if len(XPath.x_path(self.model_viewer._get_model_view(),
                                f'.//COLLECTION[@dmrole="{dmrole}"]')) != 0:
                for ele in XPath.x_path(self.model_viewer._get_model_view(),
                                        f'.//COLLECTION[@dmrole="{dmrole}"]'):
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any collections of the VOTable")
        elif all is True:
            if len(XPath.x_path(self.model_viewer._get_model_view(),
                                f'.//COLLECTION[@dmrole="{dmrole}"]')) != 0:
                ele = []
                for elem in XPath.x_path(self.model_viewer._get_model_view(),
                                         f'.//COLLECTION[@dmrole="{dmrole}"]'):
                    ele.append(elem)
                if ele:
                    return ele
            else:
                raise MivotElementNotFound(f"Cannot find dmrole {dmrole} in any collections of the VOTable")
            return ele
        return None
