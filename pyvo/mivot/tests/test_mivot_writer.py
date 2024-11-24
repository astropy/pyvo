import os
from astropy.io.votable import parse
from pyvo.utils import activate_features
from pyvo.mivot.writer.annotations import MivotAnnotations
from pyvo.mivot.writer.instance import MivotInstance
from pyvo.mivot.viewer.mivot_viewer import MivotViewer

activate_features('MIVOT') 
votable_path = os.path.realpath(os.path.join(__file__, "..", "data", "test.mivot_viewer.no_mivot.xml"))

def test_MivotAnnotations():
    mb =  MivotAnnotations()
    mb.build_mivot_block()
    
    mb.add_globals("<INSTANCE dmtype='model:type'></INSTANCE>")
    mb.add_templates("<INSTANCE dmtype='model:type.a'></INSTANCE>")
    mb.add_templates("<INSTANCE dmtype='model:type.b'></INSTANCE>")
    mb.add_model("model", "http://model.com")
    mb.add_model("model2", None)
    mb.set_report(True, "unit tests")
    mb.build_mivot_block(templates_id="azerty")
    
    print("insert @@@@@@@@@@@")
    mb.insert_into_votable(votable_path)
    
    mb.set_report(False, "unit tests")
    mb.build_mivot_block()

def test_MivotInstance():
    instance1 = MivotInstance(dmtype="model:type.inst", dmid="id1")
    instance1.add_attribute(dmtype="model:type.att1", dmrole="model:type.inst.role1",  value="value1", unit="m/s")
    instance1.add_attribute(dmtype="model:type.att2", dmrole="model:type.inst.role2",  value="value2", unit="m/s")
    instance1.add_reference(dmrole="model:type.inst.role2",  dmref="dmreference")
    
    instance2 = MivotInstance(dmtype="model:type2.inst", dmrole="model:role.instance2", dmid="id2")
    instance2.add_attribute(dmtype="model:type2.att1", dmrole="model:type2.inst.role1", value="value3", unit="m/s")
    instance2.add_attribute(dmtype="model:type2.att2", dmrole="model:type2.inst.role2", value="value4", unit="m/s")    
    instance1.add_instance(instance2)
    
    globals1 = MivotInstance(dmtype="model:type.globals", dmid="dmreference")
    globals1.add_attribute(dmtype="model:type.att1", dmrole="model:type.globals.role1",  value="value1", unit="m/s")
    globals1.add_attribute(dmtype="model:type.att2", dmrole="model:type.globals.role2",  value="value2", unit="m/s")
 
    mb =  MivotAnnotations()
    mb.add_templates(instance1)
    mb.add_globals(globals1)

    mb.build_mivot_block()
    print(mb.mivot_block)
    votable =  parse(votable_path)
    mb.insert_into_votable(votable)

    mv = MivotViewer(votable)
    print(mv.dm_instance)

if __name__ == "__main__":
    test_MivotInstance()