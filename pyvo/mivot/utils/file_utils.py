"""
Created on Feb 26, 2021

@author: laurentmichel
"""
import os


class FileUtils(object):
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
