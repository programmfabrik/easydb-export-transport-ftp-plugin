# encoding: utf-8

import sys
import os
import json
import subprocess
import urllib.parse


# --------------------- fylr specific utils ---------------------


class PluginInfoJson:

    export: dict

    api_url: str

    export_id: int
    export_name: str

    transport_uuid: str
    transport_packer: str

    target_dir: str

    ftp_params: dict
    rclone_ftp_method: str

    webdav_params: dict

    additional_parameters: list

    def __init__(self, target: str, info_json: dict) -> None:
        self.__target = target
        self.__parse(info_json)

    def format_export_http_url(self) -> str:

        path_for_packer = {
            'zip': 'zip',
            'tar.gz': 'tar_gz',
        }

        transport_packer = self.transport_packer
        if not transport_packer:
            transport_packer = 'folder'

        if transport_packer in path_for_packer:
            return f'{self.api_url}/api/v1/export/{self.export_id}/uuid/{self.transport_uuid}/{path_for_packer[transport_packer]}/'

        return f'{self.api_url}/api/v1/export/{self.export_id}/uuid/{self.transport_uuid}/file/'

    def __parse(self, info_json: dict) -> None:

        self.export = info_json.get('export', {})
        if not self.export or self.export == {}:
            raise Exception('export not set')

        self.api_url = info_json.get('api_callback', {}).get('url')
        if not self.api_url:
            raise Exception('callback url not set')

        # read from export definition
        __export_def = self.export.get('export')
        if not __export_def:
            raise Exception('export definition not set')
        self.export_id = __export_def.get('_id')
        if not self.export_id:
            raise Exception('export: id not set')
        self.export_name = __export_def.get('name')
        if not self.export_name:
            raise Exception('export: name not set')

        # read from transport definition
        __transport_def = info_json.get('transport')
        if not __transport_def:
            raise Exception('transport not set')

        self.transport_uuid = __transport_def.get('uuid')
        if not self.transport_uuid:
            raise Exception('transport.uuid not set')

        __transport_options = __transport_def.get('options')
        if not __transport_options:
            raise Exception('transport.options not set')

        self.target_dir = __transport_options.get('directory')
        if not self.target_dir:
            self.target_dir = ''
        while self.target_dir.endswith('/'):
            self.target_dir = self.target_dir[:-1]

        __login = __transport_options.get('login')
        if not __login:
            raise Exception('transport options: ftp/webdav user not set')

        __password = __transport_options.get('password')
        if not __password:
            # depending on the transport definition, the password might be marked as secure
            __password = __transport_options.get('password:secret')
        if not __password:
            raise Exception('transport options: ftp/webdav password not set')
        __obscure_pass = rclone_obscure_password(__password)

        # read and parse the url of the target server
        __url = __transport_options.get('server')
        if not __url:
            raise Exception('transport options: ftp/webdav url not set')

        # get packer to determine the source url
        self.transport_packer = __transport_options.get('packer')

        # ftp specific settings

        if self.__target == 'ftp':

            __ftp_protocol, __ftp_host, __ftp_port = parse_ftp_url(__url)

            if __ftp_protocol not in ['ftp', 'sftp', 'ftps']:
                raise Exception('unknown remote protocol {}'.format(__ftp_protocol))

            if not __ftp_host or __ftp_port == 0:
                raise Exception('invalid ftp url {0}'.format(__url))

            # build rclone ftp parameter map
            if __ftp_protocol == 'sftp':
                self.ftp_params = {
                    'sftp-host': __ftp_host,
                    'sftp-port': __ftp_port,
                    'sftp-user': __login,
                    'sftp-pass': __obscure_pass,
                }
                self.rclone_ftp_method = 'sftp'
            else:
                self.ftp_params = {
                    'ftp-host': __ftp_host,
                    'ftp-port': __ftp_port,
                    'ftp-user': __login,
                    'ftp-pass': __obscure_pass,
                }
                self.rclone_ftp_method = 'ftp'

            self.additional_parameters = []

            # ftps requires ftp over tls
            if __ftp_protocol == 'ftps':
                self.additional_parameters.append('ftp-tls')

        # webdav specific settings

        elif self.__target == 'webdav':

            # build rclone webdav parameter map
            self.webdav_params = {
                'webdav-url': __url,
            }
            if __login is not None:
                self.webdav_params['webdav-user'] = __login
            if __obscure_pass is not None:
                self.webdav_params['webdav-pass'] = __obscure_pass


# --------------------- helpers ---------------------


def run_command(
    command: str,
    parameters: list,
    verbose: bool = False,
) -> tuple[int, list[str], list[str]]:
    if verbose:
        stderr('> %s %s' % (command, ' '.join(parameters)))

    process = subprocess.Popen(
        [command] + parameters,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout_response: list[str] = []
    stderr_response: list[str] = []
    exit_code: int = 0

    if not process:
        return exit_code, stdout_response, stderr_response

    while True:
        if process.stdout:
            stdout_response.append(str(process.stdout.readline().strip()))
        if process.stderr:
            stderr_response.append(str(process.stderr.readline().strip()))

        code = process.poll()
        if code:
            exit_code = code

            if process.stdout:
                for output in process.stdout.readlines():
                    stdout_response.append(str(output))
            if process.stderr:
                for output in process.stderr.readlines():
                    stderr_response.append(str(output))

            break

    # multiply return code by -1 to get actual returncode
    # from docu: "A negative value -N indicates that the child was terminated by signal N (POSIX only)."
    if exit_code != None and exit_code < 0:
        exit_code *= -1

    return exit_code, stdout_response, stderr_response


def create_missing_dirs(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def create_missing_dirs_from_filepath(f_path: str):
    create_missing_dirs('/'.join(f_path.split('/')[:-1]))


class CommandlineErrorException(Exception):

    def __init__(self, msg: str):
        self.__msg = msg

    def __str__(self):
        return 'command line returned an error:\n' + self.__msg


def check_stderr(exit_code: int, stderr: list):
    if exit_code == 0:
        return

    # ignore all empty lines from stderr
    stderr_strings = []
    for se in stderr:
        se_str = se.decode('utf-8').strip()
        if len(se_str) < 1:
            continue
        stderr_strings.append(se_str)

    raise CommandlineErrorException(
        'exit code: %d\n%s'.format(exit_code, '\n'.join(stderr_strings))
    )


def stdout(line: str):
    sys.stdout.write(line)
    sys.stdout.write('\n')


def stderr(line: str):
    sys.stderr.write(line)
    sys.stderr.write('\n')


def fatal(line: str):
    stderr(line)
    exit(1)


def return_error(realm: str, msg: str):
    fatal(
        json.dumps(
            {
                'type': realm,
                'error': msg,
            },
            indent=4,
        )
    )


def return_json_body(msg: dict):
    stdout(json.dumps(msg, indent=4))


def parse_ftp_url(url: str) -> tuple[str, str, int]:
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
        return '', '', 0

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
        port = 0

    return scheme, hostname, port


# --------------------- rclone specific functions --------------------


def run_rclone_command(
    parameters: list[str],
    verbose: bool = False,
) -> tuple[int, list[str], list[str]]:
    # log level needs to be set to ERROR
    # otherwise the NOTICE about the missing rclone config file would be written to stderr
    # and the plugin would raise an exception even if the transport was successful
    return run_command(
        'rclone',
        parameters + ['--log-level=ERROR'],
        verbose,
    )


def add_rclone_parameters(
    parameter_map: dict,
    additional_parameters: list[str] = [],
) -> list[str]:
    parameters = [f'--{p}={parameter_map[p]}' for p in parameter_map]
    parameters += [f'--{p}' for p in additional_parameters]
    return parameters


def rclone_obscure_password(pw_cleartext: str) -> str:
    exit_code, stdout, stderr = run_rclone_command(['obscure', pw_cleartext])
    check_stderr(exit_code, stderr)

    obscure_password = str(stdout[0])
    if obscure_password.startswith('b\'') and obscure_password.endswith('\''):
        return obscure_password[2:-1]

    return obscure_password
