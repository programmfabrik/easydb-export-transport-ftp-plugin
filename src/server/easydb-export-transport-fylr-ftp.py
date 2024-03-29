#!/bin/python


import os
import sys
import json
from shared import util


def rclone_sync_to_ftp(parameter_map, rclone_ftp_method, ftp_dir, export_id, export_name, transport_uuid, api_url, api_token, additional_parameters=[]):

    http_url = util.format_export_http_url(api_url,
                                           api_token,
                                           export_id,
                                           transport_uuid=transport_uuid,
                                           transport_packer=None)

    ftp_url = ':{0}:{1}/{2}'.format(
        rclone_ftp_method,
        ftp_dir,
        export_name)

    parameter_map['http-url'] = http_url

    parameters = [
        'sync',
        ':http:',
        ftp_url
    ] + util.add_rclone_parameters(parameter_map, additional_parameters)

    exit_code, stdout, stderr = util.run_rclone_command(parameters)
    util.check_stderr(exit_code, stderr)
    return stdout


def rclone_copyurl_to_ftp(parameter_map, rclone_ftp_method, ftp_dir, export_id, export_name, transport_packer, api_url, api_token, additional_parameters=[]):

    http_url = util.format_export_http_url(api_url,
                                           api_token,
                                           export_id,
                                           transport_uuid=None,
                                           transport_packer=transport_packer)

    ftp_url = ':{0}:{1}/{2}.{3}'.format(
        rclone_ftp_method,
        ftp_dir,
        export_name,
        transport_packer)

    parameters = [
        'copyurl',
        http_url,
        ftp_url
    ] + util.add_rclone_parameters(parameter_map, additional_parameters)

    exit_code, stdout, stderr = util.run_rclone_command(parameters)
    util.check_stderr(exit_code, stderr)
    return stdout


if __name__ == '__main__':

    try:

        # read from %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        response = util.get_json_value(info_json, 'export')
        if response is None:
            raise Exception('export not set')
        basepath = os.path.abspath(os.path.dirname(__file__))

        api_callback_url = util.get_json_value(info_json, 'api_callback.url')
        if api_callback_url is None:
            raise Exception('callback url not set')
        api_callback_token = util.get_json_value(info_json, 'api_callback.token')
        if api_callback_token is None:
            raise Exception('callback token not set')

        # read from export definition
        export_def = util.get_json_value(response, 'export')
        if export_def is None:
            raise Exception('export definition not set')
        export_id = util.get_json_value(export_def, '_id')
        if export_id is None:
            raise Exception('export: id not set')
        export_name = util.get_json_value(export_def, 'name')
        if export_name is None:
            raise Exception('export: name not set')

        # read from transport definition
        transport_def = util.get_json_value(info_json, 'transport')
        if transport_def is None:
            raise Exception('transport not set')

        transport_uuid = util.get_json_value(transport_def, 'uuid')
        if transport_uuid is None:
            raise Exception('transport: uuid not set')

        ftp_target_dir = util.get_json_value(transport_def, 'options.directory')
        if ftp_target_dir is None:
            ftp_target_dir = ''
        while ftp_target_dir.endswith('/'):
            ftp_target_dir = ftp_target_dir[:-1]

        ftp_user = util.get_json_value(transport_def, 'options.login')
        if ftp_user is None:
            raise Exception('transport options: ftp user not set')

        ftp_password = util.get_json_value(transport_def, 'options.password')
        if ftp_password is None:
            # depending on the transport definition, the password might be markes as secure
            ftp_password = util.get_json_value(transport_def, 'options.password:secret')
        if ftp_password is None:
            raise Exception('transport options: ftp password not set')
        ftp_obscure_pass = util.rclone_obscure_password(ftp_password)

        # read and parse the url of the ftp target server
        ftp_url = util.get_json_value(transport_def, 'options.server')
        if ftp_url is None:
            raise Exception('transport options: ftp url not set')
        ftp_protocol, ftp_host, ftp_port = util.parse_ftp_url(ftp_url)

        # get defined packer and determine the source url
        packer = util.get_json_value(transport_def, 'options.packer')

        if ftp_protocol not in ['ftp', 'sftp', 'ftps']:
            raise Exception('unknown remote protocol {}'.format(ftp_protocol))

        if ftp_host is None or ftp_port is None:
            raise Exception('invalid ftp url {0}'.format(ftp_url))

        rclone_ftp_method = 'ftp'

        # build rclone ftp parameter map
        ftp_params = {}
        if ftp_protocol == 'sftp':
            ftp_params['sftp-host'] = ftp_host
            ftp_params['sftp-port'] = ftp_port
            ftp_params['sftp-user'] = ftp_user
            ftp_params['sftp-pass'] = ftp_obscure_pass

            rclone_ftp_method = 'sftp'
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
                transport_uuid=transport_uuid,
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

        response['_state'] = 'done'
        response['_transport_log'] = []

        util.return_json_body(response)

    except util.CommandlineErrorException as e:
        print((str(e)))
        util.return_error('rclone_error', str(e))
    except Exception as e:
        print((str(e)))
        util.return_error('internal', str(e))
