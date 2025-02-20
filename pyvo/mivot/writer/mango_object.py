'''
Created on 22 Jan 2025

@author: laurentmichel
'''
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.writer.instance import MivotInstance

POSITION_LEAVES = {"class": "EpochPosition",
                   "leaves": ["longitude", "latitude", "parallax",
                              "radialVelocity", "pmLongitude", "pmLatitude",
                              "epoch"]
                   }
CORRELATION_LEAVES = {"class": "EpochPositionCorrelations",
                      "leaves": ["longitudeParallax", "latitudeParallax",
                                 "pmLongitudeParallax", "pmlatitudeParallax",
                                 "longitudeLatitude", "pmLongitudePmLatitude",
                                 "latitudePmLatitude", "latitudePmLongitude",
                                 "longitudePmLatitude", "longitudePmLongitude",
                                 "isCovariance"]
                     }
ERROR_LEAVES = {"class": "PropertyError",
                   "leaves": ["parallax", "radialVelocity",
                              "position", "properMotion"]
                   }
BRIGHTNESS_LEAVES = {"class": "PhotometricProperty",
                   "leaves": ["value", "error"]
                   }

MODEL_PREFIX = "mango"

class MangoInstance(object):
    '''
    classdocs
    '''


    def __init__(self, table):
        '''
        Constructor
        '''
        self._table = table
        
    def _user_role_exist(self, user_role, model_roles):
    
        class_name = model_roles["class"]
        for leaf in model_roles["leaves"]:
            dmrole = f"{MODEL_PREFIX}:{class_name}.{leaf}"
            if dmrole.lower().endswith("." + user_role.lower()):
                return dmrole
        raise MappingError(f"Cannot find any attribute of class {MODEL_PREFIX}:{class_name} " +
                           f"matching {user_role} " +
                           f"Allowed roles are {model_roles['leaves']}")
    
    def _check_column(self, column_id):
        """
        return unit, ref, literal
        """
        if column_id.startswith("*"):
            return None, None, column_id.replace("*", "")
        try: 
            field = self._table.get_field_by_id_or_name(column_id)
            return str(field.unit), column_id, None
        except KeyError as keyerror:
            raise MappingError() from keyerror
       
    def _build_Symmetric1D(self, dmrole, ref):
        unit, ref, literal = self._check_column(ref)
        prop_err_instance = MivotInstance(dmtype=f"{MODEL_PREFIX}:mango:error.Symmetric1D",
                             dmrole=dmrole)
        
        prop_err_instance.add_attribute(dmtype=f"ivoa:RealQuantity",
                             dmrole=f"{MODEL_PREFIX}:error.PropertyError1D.sigma",
                             ref=ref, value=literal, unit=unit)
        return prop_err_instance
    
    def _build_2D_error(self, dmrole, mapping):
        columns = mapping["columns"]
        literals = []
        refs = []
        units = []
        for column in columns:
            unit, ref, literal = self._check_column(column)
            units.append(unit)
            literals.append(literal)
            refs.append(ref)

        err_class = mapping["class"]
        prop_err_instance = None
        if err_class in ["ErrorCorrMatrix", "ErrorCovMatrix"]:
            prop_err_instance = MivotInstance(dmtype=f"{MODEL_PREFIX}:error.{err_class}",
                             dmrole=dmrole) 
            prop_err_instance.add_attribute(dmtype=f"ivoa:RealQuantity",
                             dmrole=f"{MODEL_PREFIX}:error.{err_class}.sigma1",
                             ref=refs[0], unit=units[0])
            prop_err_instance.add_attribute(dmtype=f"ivoa:RealQuantity",
                             dmrole=f"{MODEL_PREFIX}:error.{err_class}.sigma2",
                             ref=refs[1], value=literals[1], unit=units[0])
        else:
            raise MappingError(f"2D Error type {err_class} not supported (or unknown)")
        return prop_err_instance
    
    def _get_epoch_position_correlations(self, **correlations):
        epc_instance = MivotInstance(dmtype=f"{MODEL_PREFIX}:EpochPositionCorrelations",
                                     dmrole=f"{MODEL_PREFIX}:EpochPosition.correlations")
        for role, column in correlations.items():
            if (dmrole := self._user_role_exist(role, CORRELATION_LEAVES)) and column:
                unit, ref, literal = self._check_column(column)
                epc_instance.add_attribute(dmtype="ivoa:real", dmrole=dmrole,
                                               ref=ref, value=literal, unit=unit)
        return epc_instance
     
    def _get_epoch_position_errors(self, **errors):
        err_instance = MivotInstance(dmtype=f"{MODEL_PREFIX}:EpochPositionErrors",
                                     dmrole=f"{MODEL_PREFIX}:mango:EpochPosition.errors")
        for role, column in errors.items():
            prop_err_instance = None      
            if (dmrole := self._user_role_exist(role, ERROR_LEAVES)) and column:
                if role.endswith("parallax"):
                    prop_err_instance = self._build_Symmetric1D(
                        f"{MODEL_PREFIX}:EpochPositionErrors.parallax",
                        column)
                elif role.endswith("radialVelocity"):
                    prop_err_instance = self._build_Symmetric1D(
                        f"{MODEL_PREFIX}:EpochPositionErrors.parallax",
                        column)
                elif role.endswith("position"):
                    prop_err_instance = self._build_2D_error(
                        f"{MODEL_PREFIX}:EpochPositionErrors.position",
                        column)
                elif role.endswith("properMotion"):
                    prop_err_instance = self._build_2D_error(
                        f"{MODEL_PREFIX}:EpochPositionErrors.properMotion",
                        column)
                
            if prop_err_instance:
                err_instance.add_instance(prop_err_instance)   
        return  err_instance
    

    def get_epoch_position(self, space_frame_id, time_frame_id, sky_position, correlations, errors):
        ep_instance = MivotInstance( dmtype=f"{MODEL_PREFIX}:EpochPosition")
        for role, column in sky_position.items():
            if (dmrole := self._user_role_exist(role, POSITION_LEAVES)) and column:
                unit, ref, literal = self._check_column(column)
                ep_instance.add_attribute(dmtype="ivoa:RealQuantity", dmrole=dmrole,
                                              ref=ref, value=literal, unit=unit)
                
        ep_instance.add_instance(self._get_epoch_position_correlations(**correlations))
        ep_instance.add_instance(self._get_epoch_position_errors(**errors))
        ep_instance.add_reference(dmrole=f"{MODEL_PREFIX}:EpochPosition.spaceSys", dmref=space_frame_id)
        ep_instance.add_reference(dmrole=f"{MODEL_PREFIX}:EpochPosition.timeSys", dmref=time_frame_id)
        return ep_instance

    def get_brightness(self, filter_id, mag):
        """
        Not in sync with the model yet
        """
        mag_instance = MivotInstance( dmtype=f"{MODEL_PREFIX}:PhotometricProperty")
        for role, column in mag.items():
            if (dmrole := self._user_role_exist(role, BRIGHTNESS_LEAVES)) and column:
                unit, ref, literal = self._check_column(column)
                mag_instance.add_attribute(dmtype="ivoa:RealQuantity", dmrole=dmrole,
                                              ref=ref, value=literal, unit=unit)
        mag_instance.add_reference(dmrole=f"{MODEL_PREFIX}:PhotometricProperty.photCal", dmref=filter_id)                
        return mag_instance
         
         
    @staticmethod
    def get_color():
        pass      
    
    
