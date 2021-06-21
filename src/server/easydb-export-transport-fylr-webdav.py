#!/bin/python


import os
import sys
import json
from shared import util


def rclone_sync_to_webdav(parameter_map, webdav_dir, export_id, export_name, api_url, api_token):
    parameter_map['http-url'] = util.format_export_http_url(api_url,
                                                            api_token,
                                                            export_id)
    parameters = [
        'sync',
        ':http:',
        ':webdav:{0}/{1}/'.format(
            '/{0}'.format(webdav_dir) if len(webdav_dir) > 0 else '',
            export_name)
    ] + util.add_rclone_parameters(parameter_map)

    stdout, stderr = util.run_rclone_command(parameters, True)
    util.check_stderr(stderr)
    return stdout


def rclone_copyurl_to_webdav(parameter_map, webdav_dir, export_id, export_name, transport_packer, api_url, api_token):
    http_url = util.format_export_http_url(api_url,
                                           api_token,
                                           export_id,
                                           transport_packer)
    webdav_url = ':webdav:/{0}/{1}.{2}'.format(
        '/{0}'.format(webdav_dir) if len(webdav_dir) > 0 else '',
        export_name,
        transport_packer)

    parameters = [
        'copyurl',
        http_url,
        webdav_url
    ] + util.add_rclone_parameters(parameter_map)

    stdout, stderr = util.run_rclone_command(parameters)
    util.check_stderr(stderr)
    return stdout


if __name__ == '__main__':

    try:

        # read from %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        response = util.get_json_value(info_json, 'export', True)
        basepath = os.path.abspath(os.path.dirname(__file__))

        api_callback_url = util.get_json_value(
            info_json, 'api_callback.url', True)
        api_callback_token = util.get_json_value(
            info_json, 'api_callback.token', True)

        # read from export definition
        export_def = util.get_json_value(response, 'export', True)
        export_id = util.get_json_value(export_def, '_id', True)
        export_name = util.get_json_value(export_def, 'name', True)

        # read from transport definition
        transport_def = util.get_json_value(info_json, 'transport', True)

        webdav_target_dir = util.get_json_value(
            transport_def, 'options.directory')
        if webdav_target_dir is None:
            webdav_target_dir = ''
        while webdav_target_dir.endswith('/'):
            webdav_target_dir = webdav_target_dir[:-1]

        webdav_user = util.get_json_value(transport_def, 'options.login')

        webdav_pass = util.get_json_value(transport_def, 'options.password')
        if webdav_pass is not None:
            webdav_obscure_pass = util.rclone_obscure_password(webdav_pass)
        else:
            webdav_obscure_pass = None

        # read and parse the url of the webdav target server
        webdav_url = util.get_json_value(transport_def, 'options.server', True)

        # get defined packer and determine the source url
        packer = util.get_json_value(transport_def, 'options.packer')

        # build rclone webdav parameter map
        webdav_params = {
            'webdav-url': webdav_url
        }
        if webdav_user is not None:
            webdav_params['webdav-user'] = webdav_user
        if webdav_obscure_pass is not None:
            webdav_params['webdav-pass'] = webdav_obscure_pass

        # depending on the packer, decide which rclone method to use
        if packer is None or packer == 'folder':
            # sync all exported files and folders from the export with the webdav target directory
            rclone_response = rclone_sync_to_webdav(
                parameter_map=webdav_params,
                webdav_dir=webdav_target_dir,
                export_id=export_id,
                export_name=export_name,
                api_url=api_callback_url,
                api_token=api_callback_token
            )

        elif packer in ['zip', 'tar.gz']:
            # copy the exported archive files from the export to the webdav target directory
            rclone_response = rclone_copyurl_to_webdav(
                parameter_map=webdav_params,
                webdav_dir=webdav_target_dir,
                export_id=export_id,
                export_name=export_name,
                transport_packer=packer,
                api_url=api_callback_url,
                api_token=api_callback_token
            )

        else:
            raise Exception('unknown packer {}'.format(packer))

        util.return_json_body(response)

    except util.CommandlineErrorException as e:
        print(str(e))
        util.return_error('rclone_error', str(e))
    except Exception as e:
        print(str(e))
        util.return_error('internal', str(e))
