# encoding: utf-8

import sys
import os
import re
import json
import subprocess
import urllib.parse


def get_json_value(js, path, expected=False):
    current = js
    path_parts = path.split('.')
    for path_part in path_parts:
        if not isinstance(current, dict) or path_part not in current:
            if expected:
                return_error('internal', 'expected: {0}'.format(path_part))
            else:
                return None
        current = current[path_part]
    return current


def run_command(command, parameters, verbose=False):
    if verbose:
        stderr('> %s %s' % (command, ' '.join(parameters)))

    process = subprocess.Popen([command] + parameters,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    stdout_response = []
    stderr_response = []

    while True:
        stdout_response.append(process.stdout.readline().strip())
        stderr_response.append(process.stderr.readline().strip())

        return_code = process.poll()
        if return_code is not None:
            for output in process.stdout.readlines():
                stdout_response.append(output)
            for output in process.stderr.readlines():
                stderr_response.append(output)
            break

    return stdout_response, stderr_response


def create_missing_dirs(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def create_missing_dirs_from_filepath(f_path):
    create_missing_dirs('/'.join(f_path.split('/')[:-1]))


class CommandlineErrorException(Exception):

    def __init__(self, msg):
        self.__msg = msg

    def __str__(self):
        return 'command line returned an error:\n' + self.__msg


def check_stderr(stderr):
    if len(stderr) < 1:
        return

    if len(stderr) == 1:
        if len(stderr[0]) < 1:
            return

    # check for stderr lines from rclone that actually contain information about success
    # some might be disguised as errors
    # also there can be information that certain files or directories are ignored which also is marked as an error
    inicators_rclone_success = [
        r'^.*Attempt .*succeeded$',
        r'.*Entry doesn\'t belong in directory.+- ignoring',
        r'.*SetModTime is not supported',
    ]

    # ignore all empty lines from stderr
    stderr_strings = []
    for se in stderr:
        se_str = se.decode('utf-8').strip()
        if len(se_str) < 1:
            continue
        stderr_strings.append(se_str)

    for s in stderr_strings:
        ignore = False
        for i in inicators_rclone_success:
            if re.match(i, s) is not None:
                ignore = True
                break

    if not ignore:
        raise CommandlineErrorException('\n'.join(stderr_strings))


def stdout(line):
    sys.stdout.write(line)
    sys.stdout.write('\n')


def stderr(line):
    sys.stderr.write(line)
    sys.stderr.write('\n')


def fatal(line):
    stderr(line)
    exit(1)


def return_error(realm, msg):
    fatal(json.dumps({
        'type': realm,
        'error': msg
    }, indent=4))


def return_json_body(msg):
    stdout(json.dumps(msg, indent=4))


def parse_ftp_url(url):
    url_parts = urllib.parse.urlparse(url)

    # assume protocol ftp if not specified
    scheme = url_parts.scheme if url_parts.scheme != '' else 'ftp'

    # if hostname is empty (protocol was empty), assume path as hostname
    hostname = url_parts.hostname
    if hostname == '' or hostname is None:
        if ':' in url_parts.path:
            hostname = ':'.join(url_parts.path.split(':')[:-1])
        else:
            hostname = url_parts.path
    if hostname == '' or hostname.startswith('/'):
        return None, None, None

    # assume standard port 21/22 if not specified
    if url_parts.port is not None:
        port = url_parts.port
    elif scheme == 'ftp':
        port = 21
    elif scheme == 'ftps':
        port = 21
    elif scheme == 'sftp':
        port = 22
    else:
        port = None

    return scheme, hostname, port


def format_export_http_url(api_url, api_token, export_id, transport_uuid=None, transport_packer=None):

    path_for_packer = {
        'zip': 'zip',
        'tar.gz': 'tar_gz'
    }

    if transport_packer is None:
        return '{0}/api/v1/export/{1}/uuid/{2}/file/'.format(
            api_url,
            export_id,
            transport_uuid)

    return '{0}/api/v1/export/{1}/{2}/?access_token={3}&disposition=attachment'.format(
        api_url,
        export_id,
        path_for_packer[transport_packer],
        api_token)

# --------------------- rclone specific functions --------------------


def run_rclone_command(parameters, verbose=False):
    # log level needs to be set to ERROR
    # otherwise the NOTICE about the missing rclone config file would be written to stderr
    # and the plugin would raise an exception even if the transport was successful
    return run_command('rclone',
                       parameters + ['--log-level=ERROR'],
                       verbose)


def add_rclone_parameters(parameter_map, additional_parameters=[]):
    parameters = ['--{0}={1}'.format(p, parameter_map[p])
                  for p in parameter_map]
    parameters += ['--{0}'.format(p) for p in additional_parameters]
    return parameters


def rclone_obscure_password(pw_cleartext):
    stdout, stderr = run_rclone_command([
        'obscure',
        pw_cleartext
    ])
    check_stderr(stderr)

    obscure_password = str(stdout[0])
    if obscure_password.startswith('b\'') and obscure_password.endswith('\''):
        return obscure_password[2:-1]

    return obscure_password
