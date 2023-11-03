"""
Code imported from SVOM
Created on 29 mai 2019

@author: michel
"""
import json
from pyvo.mivot import logger
from pyvo.mivot.utils.exceptions import DataFormatException
from pyvo.mivot.utils.json_encoder import MyEncoder


class DictUtils:
    """
    static class processing implementing convenient operation on dictionaries
    """

    @staticmethod
    def read_dict_from_file(filename, fatal=False):
        """
        Read a Dict in filename, rises an exception if something goes wrong.
        :param filename: filename
        :type filename: string
        :param fatal: triggers a systeml exit if true
        :type fatal: boolean
        :return: dict extracted from the file
        :rtype: python Dict
        :raise DataFormatException: if the file has a wrong format
        """
        try:
            logger.debug("Reading json from %s", filename)
            from collections import OrderedDict
            with open(filename, 'r') as file:
                retour = json.load(file, object_pairs_hook=OrderedDict)
                return retour

        except DataFormatException as exception:
            if fatal is True:
                raise DataFormatException("reading {}".format(filename))
            else:
                logger.error("{} reading {}".format(exception, filename))

    @staticmethod
    def get_pretty_json(dictionnary):
        """
        :return: A pretty string representation of the dictionary.
        :rtype: Python Dict
        """
        from collections import OrderedDict
        return json.dumps(dictionnary,
                          indent=2,
                          # sort_keys=True,
                          cls=MyEncoder)

    @staticmethod
    def print_pretty_json(dictionnary):
        """
        :return: Print out pretty string representation of the dictionary.
        """
        print(DictUtils.get_pretty_json(dictionnary))
