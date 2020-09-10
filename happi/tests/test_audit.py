from abc import ABCMeta
import argparse
from unittest.mock import patch
import happi
from happi.audit import Audit
from unittest import TestCase
import pytest
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)
audit = Audit()


@pytest.fixture(scope='function')
def happi_cfg(tmp_path, db):
    happi_cfg_path = tmp_path / 'happi.cfg'
    happi_cfg_path.write_text(f"""\
[DEFAULT]'
backend=json
path={db}
""")
    return str(happi_cfg_path.absolute())


@pytest.fixture(scope='function')
def db(tmp_path):
    dir_path = tmp_path / "db_dir"
    dir_path.mkdir()
    json_path = dir_path / 'db.json'
    json_path.write_text("""\
{
    "XRT:M3H": {
        "_id": "XRT:M3H",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "PBT",
        "creation": "Tue Feb 27 16:12:10 2018",
        "device_class": "pcdsdevices.device_types.OffsetMirror",
        "kwargs": {
            "name": "{{name}}"
        },
        "last_edit": "Tue Feb 27 16:12:10 2018",
        "macros": null,
        "name": "xrt_m3h",
        "parent": null,
        "prefix": "XRT:M3H",
        "prefix_xy": null,
        "screen": null,
        "stand": null,
        "system": "beam control",
        "type": "pcdsdevices.happi.containers.OffsetMirror",
        "xgantry_prefix": null,
        "z": 927.919
    },
    "XCS:SB2:PIM": {
        "_id": "XCS:SB2:PIM",
        "active": true,
        "args": [
            "{{prefix}}"
        ],
        "beamline": "XCS",
        "creation": "Tue Feb 27 11:15:19 2018",
        "detailed_screen": null,
        "device_class": "pcdsdevices.pim.PIMWithLED",
        "documentation": null,
        "embedded_screen": null,
        "engineering_screen": null,
        "kwargs": {
            "name": "{{name}}",
            "prefix_det": "{{prefix_det}}"
        },
        "last_edit": "Fri May 17 11:44:12 2019",
        "lightpath": false,
        "macros": null,
        "name": "xcs_sb2_pim",
        "parent": null,
        "prefix": "XCS:SB2:PIM",
        "prefix_det": "XCS:GIGE:04:",
        "screen": null,
        "stand": null,
        "system": null,
        "type": "pcdsdevices.happi.containers.LCLSItem",
        "z": 1005.72
    }
}
""")
    return str(json_path.absolute())


class CommandClassTests(TestCase):
    """
    Test that the Command class has been initialized propertly
    And that the abstract classes have raise an error if not implemented
    """
    happi.audit.Command.__abstractmethods__ = set()

    @dataclass
    class Dummy(happi.audit.Command):
        name = 'audit'
        summary = 'description'

    d = Dummy()

    with pytest.raises(NotImplementedError):
        d.add_args('a_parser')
    with pytest.raises(NotImplementedError):
        d.run('some_arg')

    assert isinstance(happi.audit.Command, ABCMeta)

    def test_constructor_fail(self):
        with pytest.raises(TypeError):
            happi.audit.Command()

    def test_constructor_partial_fail(self):
        with pytest.raises(TypeError):
            happi.audit.Command("my_name")

    def test_constructor_success(self):
        self.cmd = happi.audit.Command('a_name', 'a_description')
        expected_dict = {'name': 'a_name', 'summary': 'a_description'}
        assert self.cmd.__dict__ == expected_dict


class ValidateRunTests(TestCase):
    args = argparse.Namespace(cmd='audit', extras=True, file='db.json',
                              path=None, verbose=False, version=False)
    args2 = argparse.Namespace(cmd='audit', extras=False, file='db.json',
                               path=None, verbose=False, version=False)
    args3 = argparse.Namespace(cmd='audit', extras=False, file=None,
                               path=None, verbose=False, version=False)
    args4 = argparse.Namespace(cmd='audit', extras=True, file=None,
                               path=None, verbose=False, version=False)

    def test_validate_file_called(self):
        with patch('happi.audit.Audit.validate_file',
                   return_value=True) as mock:
            audit.run(self.args)
            assert mock.called

    def test_validate_file_called_with_false(self):
        with patch('happi.audit.Audit.validate_file', return_value=False):
            res = audit.run(self.args)
            assert res is None

    def test_check_extra_attributes_called(self):
        with patch('happi.audit.Audit.check_extra_attributes') as mock:
            audit.run(self.args)
            mock.assert_called_once()

    def test_check_extra_attributes_not_called(self):
        with patch('happi.audit.Audit.parse_database') as mock:
            audit.run(self.args2)
            mock.assert_called_once()

    def test_find_config_called(self):
        with patch('happi.client.Client.find_config',
                   return_value='happi.cfg') as mock:
            audit.run(self.args3)
            mock.assert_called_once()

    def test_find_config_called_exit(self):
        with patch('happi.client.Client.find_config',
                   return_value=None):
            with pytest.raises(SystemExit) as sys_e:
                audit.run(self.args3)
                assert sys_e.e.type == SystemExit
                assert sys_e.value.code == 1

    def test_config_parser_with_return_none(self):
        with patch('configparser.ConfigParser.get', return_value=None):
            with pytest.raises(Exception):
                res = audit.run(self.args3)
                assert res is None

    def test_validate_file_called_with_true(self):
        with patch('happi.audit.Audit.validate_file',
                   return_value=True) as mock:
            audit.run(self.args3)
            mock.assert_called_once()

    def test_config_with_parse_database(self):
        with patch('happi.audit.Audit.parse_database') as mock:
            audit.run(self.args3)
            mock.assert_called_once()

    def test_config_with_extras(self):
        with patch('happi.audit.Audit.check_extra_attributes') as mock:
            audit.run(self.args4)
            mock.assert_called_once()

    def test_config_parser_with_return_not_none(self):
        with patch('happi.audit.Audit.validate_file', return_value=False):
            with pytest.raises(SystemExit) as sys_e:
                audit.run(self.args3)
                assert sys_e.e.type == SystemExit
                assert sys_e.value.code == 1


class ValidateFileTest(TestCase):
    """
    Test validate_file
    """
    @patch('os.path.isfile', return_value=True)
    def test_validate_is_file(self, mock_file_name):
        """
        Mocking os.path.isfile and using the return value True
        """
        assert audit.validate_file("bla") is True

    @patch('os.path.isfile', return_value=False)
    def test_validate_is_not_file(self, mock_file_name):
        """
        Mocking os.path.isfile and using the return value False
        """
        assert audit.validate_file('sfsdfsf') is False


@pytest.mark.usefixtures("db")
class TestValidateContaienr(TestCase):
    """
    Test the validate_container
    """
    def test_something(self):
        pass