"""
Utility class to process dictionary.
"""
import json
from pyvo.mivot import logger
from pyvo.mivot.utils.exceptions import DataFormatException
from pyvo.mivot.utils.json_encoder import JsonEncoder


class DictUtils:
    """
    Static class implementing convenient operations on dictionaries.
    """

    @staticmethod
    def read_dict_from_file(filename, fatal=False):
        """
        Read a dictionary from a file and raise an exception if something goes wrong.

        Parameters:
        - filename (str): The filename.
        - fatal (bool): Triggers a system exit if True.

        Returns:
        - dict: The dictionary extracted from the file.

        Raises:
        - DataFormatException: If the file has an incorrect format.
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
    def _get_pretty_json(dictionnary):
        """
        Return a pretty string representation of the dictionary.

        Parameters:
        - dictionary (dict): The dictionary.

        Returns:
        - str: A pretty string representation of the dictionary.
        """
        return json.dumps(dictionnary,
                          indent=2,
                          # sort_keys=True,
                          cls=JsonEncoder)

    @staticmethod
    def print_pretty_json(dictionnary):
        """
        Print out a pretty string representation of the dictionary.

        Parameters:
        - dictionary (dict): The dictionary.
        """
        print(DictUtils._get_pretty_json(dictionnary))
