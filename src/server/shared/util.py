# encoding: utf-8

import sys
import os
import json
import subprocess
import re


class PluginInfoJson:

    export: dict

    api_url: str
    external_url: str

    export_id: int
    export_name: str

    transport_uuid: str
    transport_packer: str

    target_dir: str

    ftp_params: dict
    rclone_ftp_method: str
    rclone_log_level: str

    webdav_params: dict

    additional_parameters: list

    def __init__(self, target: str, info_json: dict, stdin_json: dict) -> None:
        self.__target = target
        self.__parse(info_json, stdin_json)

    def format_export_http_url(self) -> str:

        path_for_packer = {
            'folder': 'file',
            'zip': 'zip',
            'tar.gz': 'tar_gz',
        }

        packer = self.transport_packer
        if not packer:
            packer = 'folder'

        packer_sub_path = path_for_packer.get(packer)
        if not packer_sub_path:
            raise Exception(f'transport.options.packer {packer} is invalid')

        base_url = ''
        if self.external_url:
            # plugin frontend part can also set an external url
            base_url = self.external_url
        else:
            base_url = f'{self.api_url}/api/v1/export/{self.export_id}/uuid/{self.transport_uuid}'

        # for example:
        # - <url>/api/v1/export/1/uuid/12345674-890a-bcde-f123-4567890abcde/zip/
        # - <url>/api/v1/export/1/uuid/12345674-890a-bcde-f123-4567890abcde/tar_gz/
        # - <url>/api/v1/export/1/uuid/12345674-890a-bcde-f123-4567890abcde/file/
        return f'{base_url}/{packer_sub_path}/'

    def __parse(self, info_json: dict, stdin_json: dict) -> None:

        self.export = stdin_json.get('export', {})
        if not self.export or self.export == {}:
            raise Exception('export not set')

        self.api_url = info_json.get('api_callback', {}).get('url')
        if not self.api_url:
            raise Exception('callback url not set')

        # read from base config
        # info.config.plugin["easydb-export-transport-ftp-plugin"].config.rclone.log_level
        __plugin_config = (
            info_json.get('info', {})
            .get('plugin', {})
            .get('easydb-export-transport-ftp-plugin', {})
            .get('config', {})
        )
        self.rclone_log_level = __plugin_config.get('rclone', {}).get(
            'log_level', 'INFO'
        )

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

        self.external_url = __transport_def.get('external_url')

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

        # read and parse the url of the target server
        __url = __transport_options.get('server')
        if not __url:
            raise Exception('transport options: ftp/webdav url not set')

        # get packer to determine the source url
        self.transport_packer = __transport_options.get('packer')

        # ftp specific settings

        if self.__target == 'ftp':

            # login data
            __user = __transport_options.get('login')
            if not __user:
                raise Exception('transport options: ftp login not set')
            __pass = __transport_options.get('password')
            if not __pass:
                __pass = __transport_options.get('password:secret')
            if not __pass:
                raise Exception('transport options: ftp password not set')
            __obscure_pass = rclone_obscure_password(__pass)

            # different ftp protocols
            __ftp_protocol, __ftp_host, __ftp_port = parse_ftp_url(__url)
            if __ftp_protocol not in ['ftp', 'sftp', 'ftps']:
                raise Exception(f'unknown remote protocol {__ftp_protocol}')
            if not __ftp_host or __ftp_port == 0:
                raise Exception(f'invalid ftp url {__url}')

            # build rclone ftp parameter map
            if __ftp_protocol == 'sftp':
                self.ftp_params = {
                    'sftp-host': __ftp_host,
                    'sftp-port': __ftp_port,
                    'sftp-user': __user,
                    'sftp-pass': __obscure_pass,
                }
                self.rclone_ftp_method = 'sftp'
            else:
                self.ftp_params = {
                    'ftp-host': __ftp_host,
                    'ftp-port': __ftp_port,
                    'ftp-user': __user,
                    'ftp-pass': __obscure_pass,
                }
                self.rclone_ftp_method = 'ftp'

            self.additional_parameters = []

            # ftps requires ftp over tls
            if __ftp_protocol == 'ftps':
                self.additional_parameters.append('ftp-tls')

        # webdav specific settings

        elif self.__target == 'webdav':

            # login data
            __user = __transport_options.get('webdav_user')
            if not __user:
                raise Exception('transport options: webdav user not set')
            __pass = __transport_options.get('webdav_pass')
            if not __pass:
                __pass = __transport_options.get('webdav_pass:secret')
            if not __pass:
                raise Exception('transport options: webdav pass not set')
            __obscure_pass = rclone_obscure_password(__pass)

            # build rclone webdav parameter map
            self.webdav_params = {
                'webdav-url': __url,
                'webdav-user': __user,
                'webdav-pass': __obscure_pass,
            }


# --------------------- helpers ---------------------


def create_missing_dirs(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def create_missing_dirs_from_filepath(f_path: str):
    create_missing_dirs('/'.join(f_path.split('/')[:-1]))


def read_from_stdin() -> str:
    s = sys.stdin.read()
    sys.stdin.close()
    return s


def read_json_from_stdin() -> dict:
    js = json.loads(sys.stdin.read())
    sys.stdin.close()
    return js


def write_to_stdout(line: str):
    """
    write line to stdout
    """
    sys.stdout.write(line)
    sys.stdout.write('\n')


def write_to_stderr(line: str):
    """
    write line to stderr
    """
    sys.stderr.write(line)
    sys.stderr.write('\n')


def write_to_stderr_fatal(line: str):
    """
    write line to stderr and exit with an error code
    """
    write_to_stderr(line)
    exit(1)


def return_error(realm: str, msg: str):
    write_to_stderr_fatal(
        json.dumps(
            {
                'type': realm,
                'error': msg,
            },
            indent=4,
        )
    )


def return_json_body(msg: dict):
    """
    after this output the program must exit, so the json is valid
    """
    write_to_stdout(json.dumps(msg, indent=4))
    exit(0)


def format_export_response(
    resp: dict,
    exit_code: int,
    rclone_stdout: list[str],
    rclone_stderr: list[str],
) -> dict:
    resp['_transport_log'] = ['start rclone...'] + rclone_stdout + rclone_stderr

    if exit_code == 0:
        resp['_state'] = 'done'
        resp['_transport_log'].append('rclone finished successfully')
    else:
        resp['_state'] = 'failed'
        resp['_transport_log'].append(f'rclone failed with exit code {exit_code}')

    return resp


FTP_URL_REGEX = r'^((?P<scheme>.+):\/\/){0,1}(?P<host>[^:\/]+)(:(?P<port>\d+)){0,1}\/*$'


def parse_ftp_url(url: str) -> tuple[str, str, int]:
    scheme = ''
    host = ''
    port = 0

    match = re.match(FTP_URL_REGEX, url)
    if not match:
        return scheme, host, port

    groups = match.groupdict()
    if not groups:
        return scheme, host, port

    host = groups.get('host', '')
    if not host:
        return scheme, host, port

    # assume protocol ftp if not specified
    scheme = groups.get('scheme')
    if not scheme:
        scheme = 'ftp'

    # assume standard port 21/22 if not specified
    try:
        port = int(groups.get('port', 0))
    except Exception as e:
        port = 0

    if port == 0:
        if scheme == 'ftp':
            port = 21
        elif scheme == 'ftps':
            port = 21
        elif scheme == 'sftp':
            port = 22

    return scheme, host, port


# --------------------- rclone specific functions --------------------


def run_rclone_command(parameters: list[str]) -> tuple[int, list[str], list[str]]:

    result = subprocess.run(
        ['rclone'] + parameters,
        capture_output=True,
        text=True,
    )

    return (
        result.returncode,
        clean_rclone_output(result.stdout),
        clean_rclone_output(result.stderr),
    )


def add_rclone_parameters(
    parameter_map: dict,
    log_level: str,
    additional_parameters: list[str] = [],
) -> list[str]:
    parameters = [f'--{p}={parameter_map[p]}' for p in parameter_map]
    parameters += [f'--{p}' for p in additional_parameters]
    if log_level:
        parameters += [f'--log-level={log_level}']
    return parameters


HIDE_PASS_REGEX = r'(--(sftp|ftp|webdav)-pass\s*=\s*[^"\s]+)'


def clean_rclone_output(output: str) -> list[str]:
    """
    - split lines in stdout, stderr output
    - discard empty lines
    - hide sensitive information like ftp-pass etc
    """
    lines = []
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue

        match = re.findall(HIDE_PASS_REGEX, line)
        if not match:
            lines.append(line)
            continue

        # replace e.g. --ftp-pass=0987654321 with --ftp-pass=***
        # so that the password does not appear in events etc
        for m in match:
            line = line.replace(m[0], f'--{m[1]}-pass=***')

        lines.append(line)
    return lines


def rclone_obscure_password(pw_cleartext: str) -> str:
    exit_code, stdout, stderr = run_rclone_command(
        [
            'obscure',
            pw_cleartext,
        ]
        + add_rclone_parameters(
            {},
            log_level='ERROR',  # suppress any output, except for the actual obscured password
        )
    )
    if exit_code != 0:
        return ''

    obscure_password = str(stdout[0])
    if obscure_password.startswith('b\'') and obscure_password.endswith('\''):
        return obscure_password[2:-1]

    return obscure_password
