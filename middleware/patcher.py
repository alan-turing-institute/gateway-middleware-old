from flask import Flask, jsonify, abort, request, make_response
from flask_httpauth import HTTPBasicAuth
from .ssh import ssh
from secrets import *
import f90nml
import json
import os
from os import makedirs
from os.path import dirname
from os.path import basename
from mako.template import Template


# TODO LRM (l.mason@imperial.ac.uk): generalise to templating patch system,
# i.e. generalise to a system that is not f90 specific


def apply_patch(template_path, parameters, destination_path):
    # f90nml.patch(template_path, parameters, destination_path)
    template = Template(filename=template_path)
    with open(destination_path, "w") as f:
        f.write(template.render(parameters=parameters))


# {"source_uri":"./resources/templates/Blue.nml", "destination_path":"project/case/"}] ,
# "scripts": [ { "source_uri": "./resources/scripts/start_job.sh", "destination_path": "project/case/" }
def patch_and_transfer_template_files(template_list, parameter_patch, simulation_root):
    '''
    Apply patch to all template files
    '''

    # gathering the needed info from our secrets file
    username = SSH_USR
    hostname = SSH_HOSTNAME
    if SSH_PORT:
        port = SSH_PORT
    else:
        port = 22

    connection = ssh(hostname, username, port, debug=True)

    for template in template_list:
        template_file = template["source_uri"]
        template_filename = basename(template_file)

        destination_path = os.path.join(simulation_root,
                                        template["destination_path"])

        tmp_path = os.path.join('tmp', template["destination_path"])
        tmp_file = os.path.join(tmp_path, template_filename)
        makedirs(tmp_path, exist_ok=True)

        apply_patch(template_file, parameter_patch, tmp_file)
        connection.secure_copy(tmp_file, destination_path)


def transfer_files(object_list, simulation_root):
    '''
    Method to copy multiple files to cluster using single SSHClient connection
    '''
    # gathering the needed info from our secrets file
    username = SSH_USR
    hostname = SSH_HOSTNAME
    if SSH_PORT:
        port = SSH_PORT
    else:
        port = 22

    connection = ssh(hostname, username, port, debug=True)

    for file_object in object_list:
        print(file_object)
        file_full_path = file_object["source_uri"]
        destination_path = os.path.join(simulation_root,
                                        file_object["destination_path"])
        connection.secure_copy(file_full_path, destination_path)
    connection.close_connection()


def run_remote_script(script_name, remote_path, debug=True):

    # gathering the needed info from our secrets file
    username = SSH_USR
    hostname = SSH_HOSTNAME
    if SSH_PORT:
        port = SSH_PORT
    else:
        port = 22

    connection = ssh(hostname, username, port, debug=True)

    command = "cd {}; bash {}".format(remote_path, script_name)
    out = connection.pass_command(command)
    if debug:
        print(out)