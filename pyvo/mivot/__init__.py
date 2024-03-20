import os
from pyvo.mivot.utils.logger_setup import LoggerSetup
from pyvo.utils import activate_features

activate_features('MIVOT')

logger = LoggerSetup.get_logger()
LoggerSetup.set_debug_level()
logger.info("client package initialized")
