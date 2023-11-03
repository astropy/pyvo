"""
Created on Feb 26, 2021

@author: laurentmichel
"""
import os


class FileUtils(object):
    """
    Utility class for file and directory operations.

    This class provides static methods to retrieve directory paths related to
    the project's file structure.

    Methods:
    - get_datadir(): Get the path to the 'data' directory for tests.
    - get_projectdir(): Get the path to the project's root directory.
    - get_schemadir(): Get the path to the 'schema' directory.
    """
    file_path = os.path.dirname(os.path.realpath(__file__))

    @staticmethod
    def get_datadir():
        return os.path.realpath(os.path.join(FileUtils.file_path, "../client/tests/", "data"))

    @staticmethod
    def get_projectdir():
        return os.path.realpath(os.path.join(FileUtils.file_path, "../../../"))

    @staticmethod
    def get_schemadir():
        return os.path.realpath(os.path.join(FileUtils.file_path, "../../../", "schema"))
