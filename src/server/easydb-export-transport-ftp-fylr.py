#!/bin/python


import os
import sys
import json
from shared import util


def run_rclone_command(parameters, verbose=False):
    # log level needs to be set to ERROR
    # otherwise the NOTICE about the missing rclone config file would be written to stderr
    # and the plugin would raise an exception even if the transport was successful
    return util.run_command('rclone',
                            parameters + ['--log-level=ERROR'],
                            verbose)


def add_rclone_parameters(parameter_map, additional_parameters=[]):
    parameters = map(lambda p: '--{0}={1}'.format(p, parameter_map[p]),
                     parameter_map)
    parameters += map(lambda p: '--{0}'.format(p),
                      additional_parameters)
    return parameters


def rclone_obscure_password(pw_cleartext):
    stdout, stderr = run_rclone_command([
        'obscure',
        pw_cleartext
    ])
    util.check_stderr(stderr)
    return stdout[0]


def rclone_sync_to_ftp(parameter_map, rclone_ftp_method, ftp_dir, export_id, export_name, api_url, api_token, additional_parameters=[]):

    http_url = '{0}/export/{1}/uuid/{2}/file/'.format(
        api_url,
        export_id,
        api_token)

    ftp_url = ':{0}:{1}/{2}'.format(
        rclone_ftp_method,
        ftp_dir,
        export_name)

    parameter_map['http-url'] = http_url

    parameters = [
        'sync',
        ':http:',
        ftp_url
    ] + add_rclone_parameters(parameter_map, additional_parameters)

    stdout, stderr = run_rclone_command(parameters, True)
    util.check_stderr(stderr)
    return stdout


def rclone_copyurl_to_ftp(parameter_map, rclone_ftp_method, ftp_dir, export_id, export_name, transport_packer, api_url, api_token, additional_parameters=[]):

    path_for_packer = {
        'zip': 'zip',
        'tar.gz': 'tar_gz'
    }

    http_url = '{0}/export/{1}/{2}/?token={3}&disposition=attachment'.format(
        api_url,
        export_id,
        path_for_packer[transport_packer],
        api_token)

    ftp_url = ':{0}:{1}/{2}.{3}'.format(
        rclone_ftp_method,
        ftp_dir,
        export_name,
        transport_packer)

    parameters = [
        'copyurl',
        http_url,
        ftp_url
    ] + add_rclone_parameters(parameter_map, additional_parameters)

    stdout, stderr = run_rclone_command(parameters, True)
    util.check_stderr(stderr)
    return stdout


def get_json(js, path, expected=False):
    # wrapper for the get_json_value function with exception handling
    try:
        return util.get_json_value(js, path, expected)
    except Exception as e:
        util.return_error('internal', str(e))


if __name__ == '__main__':

    try:

        # read from %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        response = get_json(info_json, 'export', True)
        basepath = os.path.abspath(os.path.dirname(__file__))

        api_callback_url = get_json(info_json, 'api_callback.url', True)
        api_callback_token = get_json(info_json, 'api_callback.token', True)

        # read from export definition
        export_def = get_json(response, 'export', True)
        export_id = get_json(export_def, '_id', True)
        export_name = get_json(export_def, 'name', True)

        # read from transport definition
        transport_def = get_json(info_json, 'transport', True)

        ftp_target_dir = get_json(
            transport_def,
            'options.directory',
            True)
        ftp_user = get_json(
            transport_def,
            'options.login',
            True)
        ftp_obscure_pass = rclone_obscure_password(get_json(
            transport_def,
            'options.password',
            True))

        # read and parse the url of the ftp target server
        ftp_url = get_json(transport_def, 'options.server', True)
        ftp_protocol, ftp_host, ftp_port = util.parse_ftp_url(ftp_url)

        # get defined packer and determine the source url
        packer = get_json(transport_def, 'options.packer')

        if ftp_protocol not in ['ftp', 'sftp', 'ftps']:
            raise Exception('unknown ftp protocol {}'.format(ftp_protocol))

        rclone_ftp_method = (ftp_protocol == 'sftp') and 'sftp' or 'ftp'

        if ftp_host is None or ftp_port is None:
            raise Exception('invalid ftp url {0}'.format(ftp_url))

        # build rclone ftp parameter map
        ftp_params = {}
        if ftp_protocol == 'sftp':
            ftp_params['sftp-host'] = ftp_host
            ftp_params['sftp-port'] = ftp_port
            ftp_params['sftp-user'] = ftp_user
            ftp_params['sftp-pass'] = ftp_obscure_pass
        else:
            ftp_params['ftp-host'] = ftp_host
            ftp_params['ftp-port'] = ftp_port
            ftp_params['ftp-user'] = ftp_user
            ftp_params['ftp-pass'] = ftp_obscure_pass

        additional_parameters = []

        # ftps requires ftp over tls
        if ftp_protocol == 'ftps':
            additional_parameters.append('ftp-tls')

        # depending on the packer, decide which rclone method to use
        if packer is None or packer == 'folder':
            # sync all exported files and folders from the export with the ftp target directory
            rclone_response = rclone_sync_to_ftp(
                parameter_map=ftp_params,
                rclone_ftp_method=rclone_ftp_method,
                ftp_dir=ftp_target_dir,
                export_id=export_id,
                export_name=export_name,
                api_url=api_callback_url,
                api_token=api_callback_token,
                additional_parameters=additional_parameters
            )

        elif packer in ['zip', 'tar.gz']:
            # copy the exported archive files from the export to the ftp target directory
            rclone_response = rclone_copyurl_to_ftp(
                parameter_map=ftp_params,
                rclone_ftp_method=rclone_ftp_method,
                ftp_dir=ftp_target_dir,
                export_id=export_id,
                export_name=export_name,
                transport_packer=packer,
                api_url=api_callback_url,
                api_token=api_callback_token,
                additional_parameters=additional_parameters
            )

        else:
            raise Exception('unknown packer {}'.format(packer))

    except util.RcloneException as e:
        print e
        exit(1)
