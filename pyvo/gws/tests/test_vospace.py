#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia2 against remote services
"""
import pytest

from pyvo.gws.vospace import Node, DataNode, ContainerNode, LinkNode, IVOA_DATETIME_FORMAT, ReaderWriter
from datetime import datetime


class TestVOSpace():
    # Tests VOSpace related classes

    def test_data_node(self):
        assert DataNode('foo') == DataNode('foo')
        assert DataNode('foo') != DataNode('foo', busy=True)
        assert DataNode('foo') != DataNode('notfoo')
        assert DataNode('foo', busy=True) != DataNode('notfoo')

        def get_expected_dn():
            exp_owner = 'boss'
            exp_is_public = False
            exp_ro_groups = ['ivo://authority/gms?gr1', 'ivo://authority/gms?gr2']
            exp_wr_groups = ['ivo://authority/gms?gr3', 'ivo://authority/gms?gr4']
            exp_properties = {'myprop': 123}
            exp_last_mod = datetime.strptime('2020-09-25T20:36:06.317', IVOA_DATETIME_FORMAT)
            exp_length = 33
            exp_content_checksum = 'md5:abc'
            exp_content_type = 'fits'
            dn = DataNode('foo')
            dn.owner = exp_owner
            dn.is_public = exp_is_public
            for gr in exp_ro_groups:
                dn.ro_groups.append(gr)
            for gr in exp_wr_groups:
                dn.wr_groups.append(gr)
            for key in exp_properties.keys():
                dn.properties[key] = exp_properties[key]
            dn._last_mod = exp_last_mod
            dn._length = exp_length
            dn._content_checksum = exp_content_checksum
            dn._content_type = exp_content_type
            return dn

        expected = get_expected_dn()
        actual = get_expected_dn()
        # try to break it by changing on attribute at the time
        assert expected == actual
        actual.owner = 'me'
        assert expected != actual
        actual.owner = expected.owner
        actual.is_public = not expected.is_public
        assert expected != actual
        actual.is_public = expected.is_public
        actual.ro_groups.pop(0)
        assert expected != actual
        actual.ro_groups.append('ivo://authority/gms?gr4')
        assert expected != actual
        actual = get_expected_dn()
        actual.wr_groups.append('ivo://authority/gms?gr5')
        assert expected != actual
        actual = get_expected_dn()
        for key in expected.properties.keys():
            actual.properties[key] = 'changed'
        assert expected != actual
        for key in expected.properties.keys():
            actual.properties[key] = expected.properties[key]
        assert expected == actual
        actual._last_mod = datetime.now()
        assert expected != actual
        actual._last_mod = expected.last_mod
        actual._length = 222
        assert expected != actual
        actual._length = expected.length
        actual._content_checksum = 'md5:123'
        assert expected != actual
        actual._content_checksum = expected.content_checksum
        actual._content_type = 'changed'
        assert expected != actual

    def test_container_node(self):
        expected = ContainerNode('cont')
        actual = ContainerNode('cont')
        assert expected == actual
        expected_data_child = DataNode('child-data')
        expected.add(expected_data_child)
        actual_data_child = DataNode('child-data')
        actual.add(actual_data_child)
        assert expected == actual
        assert len(actual.list_children()) == 1
        assert actual.list_children()[0] == expected_data_child
        actual._children.clear()
        assert expected != actual
        actual.add(DataNode('child-data2'))
        assert expected != actual
        actual.add(actual_data_child)
        assert expected != actual
        actual._children.clear()
        actual.add(actual_data_child)
        assert expected == actual

        # try to add a child with same name but different type
        with pytest.raises(ValueError):
            actual.add(actual_data_child)
        with pytest.raises(ValueError):
            actual.add(ContainerNode('child-data'))
        with pytest.raises(AttributeError):
            actual.remove('non-existent')

        # same child name, different type
        expected.add(ContainerNode('child-container'))
        actual.add(LinkNode('child-container', target=None))
        assert expected != actual

        actual.remove('child-container')
        actual.add(ContainerNode('child-container'))
        assert expected == actual

        expected.add(LinkNode('child-link', target=None))
        actual.add(LinkNode('child-link', target=None))
        assert expected == actual

        # change attribute in superclass
        expected.owner = 'me'
        assert expected != actual
        actual.owner = 'me'
        assert expected == actual

        # change attribute in child
        expected_data_child._content_checksum = 'md5:abc'
        assert expected != actual
        actual_data_child._content_checksum = 'md5:abc'
        assert expected == actual

    def test_link_node(self):
        expected = LinkNode('link-node', None)
        actual = LinkNode('link-node', target=None)
        assert expected == actual
        expected._target = 'vos:target/abc'
        assert expected != actual
        actual._target = 'vos:target/abc'
        assert expected == actual
        # change attribute in superclass
        expected.owner = 'me'
        assert expected != actual
        actual.owner = 'me'
        assert expected == actual


class TestReaderWriter:

    def test_parse_simple_node(self):
        source = '''
        <vos:node uri="vos://authority~vault/test" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:vos="http://www.ivoa.net/xml/VOSpace/v2.0" xsi:type="vos:ContainerNode">
        </vos:node>
        '''
        result = ReaderWriter.from_xml(source)
        assert isinstance(result, Node)
        assert result.path == "test"
        assert result.owner is None
        assert result.is_public is False
        assert result.ro_groups == []
        assert result.wr_groups == []
        assert result.properties == {}
        assert result.last_mod is None
        assert result._length is None

    def test_parse_node_with_properties(self):
        source = '''
        <vos:node uri="vos://authority~vault/test" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:vos="http://www.ivoa.net/xml/VOSpace/v2.0" xsi:type="vos:ContainerNode">
            <vos:properties>
                <vos:property uri="ivo://ivoa.net/vospace/core#creator" readonly="false">John Doe</vos:property>
                <vos:property uri="ivo://ivoa.net/vospace/core#date" readonly="true">2022-01-01T00:00:00.123</vos:property>
                <vos:property uri="ivo://ivoa.net/vospace/core#groupread" readonly="true">group1 group2</vos:property>
                <vos:property uri="ivo://ivoa.net/vospace/core#groupwrite" readonly="true">group3 group4</vos:property>
                <vos:property uri="ivo://auth/vospace#myprop" readonly="false">myval</vos:property>
            </vos:properties>
            <vos:nodes>
                <vos:node uri="vos://authority~vault/test/child1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:vos="http://www.ivoa.net/xml/VOSpace/v2.0" xsi:type="vos:DataNode">
                    <vos:properties>
                        <vos:property uri="ivo://ivoa.net/vospace/core#creator" readonly="false">Jane Smith</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#date" readonly="true">2022-02-01T00:00:00.1</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#groupread" readonly="true">group5 group6</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#groupwrite" readonly="true">group7 group8</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#length" readonly="false">33</vos:property>
                        <vos:property uri="ivo://auth/vospace#myprop" readonly="false">myval2</vos:property>
                    </vos:properties>
                </vos:node>
                <vos:node uri="vos://authority~vault/test/child2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:vos="http://www.ivoa.net/xml/VOSpace/v2.0" xsi:type="vos:LinkNode">
                    <vos:target>vos://authority~vault/test/child1</vos:target>
                    <vos:properties>
                        <vos:property uri="ivo://ivoa.net/vospace/core#creator" readonly="false">Jane Smith</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#date" readonly="true">2022-03-01T00:00:00.2</vos:property>
                        <vos:property uri="ivo://auth/vospace#myprop" readonly="false">myval3</vos:property>
                    </vos:properties>
                </vos:node>
                <vos:node uri="vos://authority~vault/test/child3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:vos="http://www.ivoa.net/xml/VOSpace/v2.0" xsi:type="vos:ContainerNode">
                    <vos:properties>
                        <vos:property uri="ivo://ivoa.net/vospace/core#creator" readonly="false">John Doe</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#date" readonly="true">2022-04-01T00:00:00.3</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#groupread" readonly="true">group9 group10</vos:property>
                        <vos:property uri="ivo://ivoa.net/vospace/core#groupwrite" readonly="true">group11 group12</vos:property>
                    </vos:properties>
                </vos:node>
            </vos:nodes>
        </vos:node>
        '''
        result = ReaderWriter.from_xml(source)
        assert isinstance(result, ContainerNode)
        assert result.path == 'test'
        assert result.owner == 'John Doe'
        assert result.is_public is False
        assert result.ro_groups == ['group1', 'group2']
        assert result.wr_groups == ['group3', 'group4']
        assert result.properties == {
            'ivo://auth/vospace#myprop': Node.NodeProperty(
                'ivo://auth/vospace#myprop', 'myval', False)
        }
        assert (result.last_mod == datetime.strptime(
            '2022-01-01T00:00:00.123', IVOA_DATETIME_FORMAT))
        assert result._length is None
        assert len(result.list_children()) == 3
        for child in result.list_children():
            if isinstance(child, DataNode):
                assert child.path == 'test/child1'
                assert child.name == 'child1'
                assert child.ro_groups == ['group5', 'group6']
                assert child.wr_groups == ['group7', 'group8']
                assert (child.last_mod == datetime.strptime(
                    '2022-02-01T00:00:00.1', IVOA_DATETIME_FORMAT))
                assert child.length == 33
                assert child.properties == {'ivo://auth/vospace#myprop': Node.NodeProperty(
                       'ivo://auth/vospace#myprop', 'myval2', False)
                }
            elif isinstance(child, LinkNode):
                assert child.path == 'test/child2'
                assert child.name == 'child2'
                assert child.ro_groups == []
                assert child.wr_groups == []

                assert child.last_mod == datetime.strptime('2022-03-01T00:00:00.2', IVOA_DATETIME_FORMAT)
                assert child.properties == {
                    'ivo://auth/vospace#myprop': Node.NodeProperty(
                        'ivo://auth/vospace#myprop', 'myval3', False)
                }
            elif isinstance(child, ContainerNode):
                assert child.path == 'test/child3'
                assert child.name == 'child3'
                assert child.ro_groups == ['group9', 'group10']
                assert child.wr_groups == ['group11', 'group12']
                assert child.last_mod == datetime.strptime('2022-04-01T00:00:00.3', IVOA_DATETIME_FORMAT)
                assert child.properties == {}
            else:
                assert False, 'Unknown type ' + str(type(child))
