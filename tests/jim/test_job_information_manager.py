import os
import re
import unittest.mock as mock
from middleware.job_information_manager import job_information_manager as JIM
from middleware.ssh import ssh
from tests.job.new_jobs import new_job5
from instance.config import *
from middleware.job.schema import Template, job_to_json


def abstract_getting_secrets():
    # This block allows us to test against local secrets or the
    # defaults generated when running our CI tests.
    secrets = [
        'SSH_USR', 'SSH_HOSTNAME', 'SSH_PORT', 'SIM_ROOT', 'PRIVATE_KEY_PATH']
    if all(x in globals() for x in secrets):
        username = SSH_USR
        hostname = SSH_HOSTNAME
        port = SSH_PORT
        simulation_root = SIM_ROOT
        private_key_path = PRIVATE_KEY_PATH
    else:
        username = 'test_user'
        hostname = 'test_host'
        port = 22
        simulation_root = '/home/'
        private_key_path = None

    return username, hostname, port, simulation_root, private_key_path


def mock_mkdir(path, exist_ok=True):
    return True


def mock_apply_patch(template_path, parameters, destination_path):
    return template_path, parameters, destination_path


def mock_secure_copy(full_file_path, destination_path):
    return full_file_path, destination_path


def mock_close():
    return True


def mock_run_remote(script_name, remote_path, debug=True):
    return script_name, 'err', '0'


class TestJIM(object):

    def test_constructor_no_simulation_root(self):

        username, hostname, port, simulation_root, private_key_path = \
            abstract_getting_secrets()

        # Create a manager
        job = new_job5()
        jim = JIM(job)

        assert jim.username == username
        assert jim.hostname == hostname
        assert jim.port == port
        assert jim.job_id == job.id
        assert jim.template_list == job.templates
        assert jim.families == job.families
        assert jim.script_list == job.scripts
        assert jim.inputs_list == job.inputs
        assert jim.simulation_root == simulation_root
        assert jim.private_key_path == private_key_path
        assert jim.patched_templates == []
        assert jim.user == job.user

    def test_apply_patch(self, tmpdir):
        job = new_job5()
        manager = JIM(job)

        # create dict objects for parameters and templates
        job_json = job_to_json(job)
        families = job_json.get("families")
        parameters = families[0].get("parameters")
        parameter = parameters[0]  # choose first parameter

        templates = job_json.get("templates")
        template = templates[0]  # choose first template

        template_path = template.get("source_uri")
        in_parameter_value = parameter.get("value")

        template_filename = os.path.basename(template_path)
        destination_path = os.path.join(tmpdir.strpath, template_filename)

        manager._apply_patch(template_path, parameters, destination_path)

        # read patched file
        with open(destination_path, "r") as f:
            content = f.readlines()

        for line in content:
            patched = re.search(r"^\s+viscosity_phase_1\s+=\s+(\S+)\s+!", line)
            if patched:
                patched_value = patched.group(1)
                assert patched_value == in_parameter_value
                break

    @mock.patch('middleware.job_information_manager.job_information_manager.'
                '_apply_patch', side_effect=mock_apply_patch)
    def test_patched_templates_construction(self, mock_patch):
        job = new_job5()
        manager = JIM(job)

        manager.patch_all_templates()

        dest = job.templates[0].destination_path
        src = os.path.join('tmp', dest,
                           os.path.basename(job.templates[0].source_uri))

        expected = [Template(source_uri=src, destination_path=dest)]
        assert manager.patched_templates == expected

    @mock.patch('os.makedirs', side_effect=mock_mkdir)
    @mock.patch('middleware.job_information_manager.job_information_manager.'
                '_apply_patch', side_effect=mock_apply_patch)
    def test_patch_templates_path_construction(self, mock_patch, mock_mkdirs):
        job = new_job5()
        manager = JIM(job)
        manager.patch_all_templates()

        calls = mock_patch.call_args[0]

        exp_filename = os.path.basename(job.templates[0].source_uri)
        exp_path_1 = job.templates[0].source_uri
        exp_path_2 = os.path.join('tmp',
                                  job.templates[0].destination_path,
                                  exp_filename)

        assert calls[0] == exp_path_1
        assert calls[2] == exp_path_2

    @mock.patch('middleware.ssh.ssh.close_connection', side_effect=mock_close)
    @mock.patch('middleware.ssh.ssh.secure_copy', side_effect=mock_secure_copy)
    def test_transfer_all_files(self, mock_copy, mock_close):
        username, hostname, port, simulation_root, private_key_path = \
            abstract_getting_secrets()
        job = new_job5()
        manager = JIM(job)
        with mock.patch.object(ssh, '__init__',
                               lambda self, *args, **kwargs: None):
            manager.transfer_all_files()
            calls = mock_copy.call_args[0]

        job_working_directory_name = "{}-{}".format(job.case.label, job.id)

        expected_path = os.path.join(
            simulation_root,
            job_working_directory_name,
            job.scripts[0].destination_path)

        assert calls[1] == expected_path

    @mock.patch('middleware.job_information_manager.job_information_manager.'
                '_run_remote_script', side_effect=mock_run_remote)
    def test_trigger_action_script_valid_verbs(self, mock_run):
        # Test that the 4 verbs work
        for verb in ['RUN', 'SETUP', 'CANCEL', 'PROGRESS']:

            job = new_job5()
            manager = JIM(job)
            message, code = manager.trigger_action_script(verb)

            first_arg = mock_run.call_args[0][0]

            exp_message = {'stdout': '{}'.format(first_arg),
                           'stderr': 'err', 'exit_code': '0'}

            assert code == 200
            assert message == exp_message

    @mock.patch('middleware.job_information_manager.job_information_manager.'
                '_run_remote_script', side_effect=mock_run_remote)
    def test_trigger_action_script_invalid_verb(self, mock_run):
        job = new_job5()
        action = 'JUMP'
        manager = JIM(job)
        message, code = manager.trigger_action_script(action)

        exp_message = {'message': '{} script not found'.format(action)}

        assert code == 400
        assert message == exp_message
