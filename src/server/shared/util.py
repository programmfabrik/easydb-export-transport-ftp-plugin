# encoding: utf-8

import sys
import os
import json
import subprocess
import urlparse


def get_json_value(js, path, expected=False):
    current = js
    path_parts = path.split('.')
    for path_part in path_parts:
        if not isinstance(current, dict) or path_part not in current:
            if expected:
                raise Exception('expected: {0}'.format(path_part))
            else:
                return None
        current = current[path_part]
    return current


def run_command(command, parameters, verbose=False):
    if verbose:
        print '>', command, ' '.join(parameters)

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


class RcloneException(Exception):

    def __init__(self, msg_lines):
        self.msg_lines = msg_lines

    def __str__(self):
        return 'rclone raised an error:\n' + '\n'.join(self.msg_lines)


def check_stderr(stderr):
    if len(stderr) < 1:
        return

    if len(stderr) == 1:
        if len(stderr[0]) < 1:
            return

    raise RcloneException(stderr)


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


def parse_ftp_url(url):
    url_parts = urlparse.urlparse(url)

    # assume protcol ftp if not specified
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
        port = 990
    elif scheme == 'sftp':
        port = 22
    else:
        port = None

    return scheme, hostname, port


def build_source_url(export_id, packer):
    return 'export/{}/{}'.format(export_id, packer)
