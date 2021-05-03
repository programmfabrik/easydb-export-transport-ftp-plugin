#!/bin/python


import os
import sys
import json
from shared import util


def run_rclone_command(parameters, verbose=False):
    return util.run_command('rclone',
                            parameters + ['--log-level=ERROR'],
                            verbose)


def rclone_obscure_password(pw_cleartext):
    stdout, stderr = run_rclone_command(['obscure', pw_cleartext])
    util.check_stderr(stderr)
    return stdout[0]


def rclone_sync(source, target, parameter_map, additional_parameters=[]):
    parameters = ['sync', '--dry-run', source, target]  # XXX
    parameters += map(lambda p: '--{0}={1}'.format(p, parameter_map[p]),
                      parameter_map)
    parameters += map(lambda p: '--{0}'.format(p),
                      additional_parameters)

    stdout, stderr = run_rclone_command(parameters, True)
    util.check_stderr(stderr)
    return stdout


def rclone_sync_to_ftp(ftp_dir, ftp_host, ftp_user, ftp_pass, ftp_protocol, api_callback_url, source_dir, api_callback_token, ftp_port):

    params = {
        'http-url': api_callback_url,
        'http-headers': "'x-easydb-token,%s'" % api_callback_token
    }
    http_source = ':http:{}'.format(source_dir)

    if ftp_protocol in ['ftp', 'ftps']:
        params['ftp-host'] = ftp_host
        params['ftp-port'] = ftp_port
        params['ftp-user'] = ftp_user
        params['ftp-pass'] = rclone_obscure_password(ftp_pass)
        return rclone_sync(source=http_source,
                           target=':ftp:/{}'.format(ftp_dir),
                           parameter_map=params,
                           additional_parameters=['--ftp-tls'] if ftp_protocol == 'ftps' else [])
    elif ftp_protocol == 'sftp':
        params['sftp-host'] = ftp_host
        params['sftp-port'] = ftp_port
        params['sftp-user'] = ftp_user
        params['sftp-pass'] = rclone_obscure_password(ftp_pass)
        return rclone_sync(source=http_source,
                           target=':sftp:/{}'.format(ftp_dir),
                           parameter_map=params)

    return None


def get_json(js, path, expected=False):
    # wrapper for the get_json_value function with exception handling
    try:
        return util.get_json_value(js, path, expected)
    except Exception as e:
        util.return_error('internal', str(e))


PLUGIN_ACTION = 'transport_ftp?ftp'


if __name__ == '__main__':

    try:

        # read from %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        response = get_json(info_json, 'export', True)

        export_def = get_json(response, 'export', True)
        export_id = get_json(export_def, '_id', True)

        transport_def = get_json(info_json, 'transport', True)

        api_callback_url = get_json(info_json, 'api_callback.url', True)
        api_callback_token = get_json(info_json, 'api_callback.token', True)

        basepath = os.path.abspath(os.path.dirname(__file__))

        # read and parse the url of the ftp target server
        ftp_url = get_json(transport_def, 'options.server', True)
        ftp_protocol, ftp_host, ftp_port = util.parse_ftp_url(ftp_url)

        if ftp_protocol not in ['ftp', 'sftp', 'ftps']:
            raise Exception('unknown ftp protocol {}'.format(ftp_protocol))

        if ftp_host is None or ftp_port is None:
            raise Exception('invalid ftp url {0}'.format(ftp_url))

        # get defined packer and determine the source url
        packer = get_json(transport_def, 'options.packer')

        if packer is None or packer == 'folder':
            source_dir = util.build_source_url(export_id, 'file')
        elif packer == 'zip':
            source_dir = util.build_source_url(export_id, 'zip')
        elif packer == 'tar.gz':
            source_dir = util.build_source_url(export_id, 'tar_gz')
        else:
            raise Exception('unknown packer {}'.format(packer))

        print rclone_sync_to_ftp(get_json(transport_def,
                                          'options.directory',
                                          True),
                                 ftp_host,
                                 get_json(transport_def,
                                          'options.login',
                                          True),
                                 get_json(transport_def,
                                          'options.password',
                                          True),
                                 ftp_protocol,
                                 api_callback_url,
                                 source_dir,
                                 api_callback_token,
                                 ftp_port)

    except util.RcloneException as e:
        print e
        exit(1)
