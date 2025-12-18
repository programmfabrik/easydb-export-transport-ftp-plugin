#!/bin/python


import sys
import json
from shared import util


def rclone_sync_to_webdav(opts: util.PluginInfoJson) -> list[str]:
    parameter_map = opts.webdav_params.copy()
    parameter_map['http-url'] = opts.format_export_http_url()

    parameters = [
        'sync',
        ':http:',
        ':webdav:{0}/{1}/'.format(
            '/{0}'.format(opts.target_dir) if len(opts.target_dir) > 0 else '',
            opts.export_name,
        ),
    ] + util.add_rclone_parameters(parameter_map)

    exit_code, stdout, stderr = util.run_rclone_command(parameters, verbose=False)
    util.check_stderr(exit_code, stderr)
    return stdout


def rclone_copyurl_to_webdav(opts: util.PluginInfoJson) -> list[str]:
    http_url = opts.format_export_http_url()
    webdav_url = ':webdav:/{0}/{1}.{2}'.format(
        '/{0}'.format(opts.target_dir) if len(opts.target_dir) > 0 else '',
        opts.export_name,
        opts.transport_packer,
    )

    parameters = [
        'copyurl',
        http_url,
        webdav_url,
    ] + util.add_rclone_parameters(opts.webdav_params)

    exit_code, stdout, stderr = util.run_rclone_command(parameters, verbose=False)
    util.check_stderr(exit_code, stderr)
    return stdout


if __name__ == '__main__':

    try:
        # read export data from stdin
        export_json = json.loads(sys.stdin.read())

        # read %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        parsed_opts = util.PluginInfoJson('webdav', info_json, export_json)
        export_response = parsed_opts.export

        # depending on the packer, decide which rclone method to use
        if (
            parsed_opts.transport_packer is None
            or parsed_opts.transport_packer == 'folder'
        ):
            # sync all exported files and folders from the export with the webdav target directory
            _ = rclone_sync_to_webdav(parsed_opts)

        elif parsed_opts.transport_packer in ['zip', 'tar.gz']:
            # copy the exported archive files from the export to the webdav target directory
            _ = rclone_copyurl_to_webdav(parsed_opts)

        else:
            raise Exception(f'unknown packer {parsed_opts.transport_packer}')

        export_response['_state'] = 'done'
        util.return_json_body(export_response)

    except util.CommandlineErrorException as e:
        util.return_error('rclone_error', str(e))
    except Exception as e:
        util.return_error('internal', str(e))
