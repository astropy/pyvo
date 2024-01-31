"""
Global logger setup
Must be used by the whole application

The default format can be restored at any time with LoggerSetup.set_default_format()
The log level can be set at any time with LoggerSetup.set_debug/info/warning/error_level
The level is set at INFO by default
"""
import sys
import logging
from pyvo.utils import prototype_feature


@prototype_feature('MIVOT')
class LoggerSetup:
    """
    Manage the logger setup.
    """
    __default_level = logging.INFO

    @staticmethod
    def get_logger():
        """
        Format and return the system logger.

        Returns
        -------
        logger
            System logger.
        """
        LoggerSetup._set_default_format()
        return logging.getLogger("mivot")

    @staticmethod
    def _set_default_format():
        """
        Set the default message format.
        """
        logging.basicConfig(stream=sys.stdout,
                            format='%(levelname)7s'
                                   ' - [%(filename)s:%(lineno)3s'
                                   ' - %(funcName)10s()] - %(message)s',
                            # datefmt="%Y-%m-%d %H:%M:%S"
                            )
        LoggerSetup._restore_default_level()

    @staticmethod
    def _restore_default_level():
        """
        Restore the message level with the last value set by a setter.
        INFO by default
        """
        logging.getLogger().setLevel(LoggerSetup.__default_level)

    @staticmethod
    def set_debug_level():
        """
        Switch to debug level.
        """
        LoggerSetup.__default_level = logging.DEBUG
        logging.getLogger().setLevel(logging.DEBUG)

    @staticmethod
    def set_info_level():
        """
        Switch to info level.
        """
        LoggerSetup.__default_level = logging.INFO
        logging.getLogger().setLevel(logging.INFO)

    @staticmethod
    def set_warning_level():
        """
        Switch to warning level.
        """
        LoggerSetup.__default_level = logging.WARN
        logging.getLogger().setLevel(logging.WARN)

    @staticmethod
    def set_error_level():
        """
        Switch to error level.
        """
        LoggerSetup.__default_level = logging.ERROR
        logging.getLogger().setLevel(logging.ERROR)
