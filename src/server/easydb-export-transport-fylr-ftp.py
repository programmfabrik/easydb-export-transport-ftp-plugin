#!/bin/python


import sys
import json
from shared import util


def rclone_sync_to_ftp(opts: util.PluginInfoJson) -> list[str]:

    http_url = opts.format_export_http_url()

    ftp_url = f':{opts.rclone_ftp_method}:{opts.target_dir}/{opts.export_name}'

    parameter_map = opts.ftp_params.copy()
    parameter_map['http-url'] = http_url

    parameters = [
        'sync',
        ':http:',
        ftp_url,
    ] + util.add_rclone_parameters(
        parameter_map,
        opts.additional_parameters,
    )

    exit_code, stdout, stderr = util.run_rclone_command(parameters)
    util.check_stderr(exit_code, stderr)
    return stdout


def rclone_copyurl_to_ftp(opts: util.PluginInfoJson) -> list[str]:

    http_url = opts.format_export_http_url()

    ftp_url = f':{opts.rclone_ftp_method}:{opts.target_dir}/{opts.export_name}.{opts.transport_packer}'

    parameters = [
        'copyurl',
        http_url,
        ftp_url,
    ] + util.add_rclone_parameters(
        opts.ftp_params,
        opts.additional_parameters,
    )

    exit_code, stdout, stderr = util.run_rclone_command(parameters)
    util.check_stderr(exit_code, stderr)
    return stdout


if __name__ == '__main__':

    try:

        # read from %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        parsed_opts = util.PluginInfoJson('ftp', info_json)
        export_response = parsed_opts.export

        # depending on the packer, decide which rclone method to use
        if not parsed_opts.transport_packer or parsed_opts.transport_packer == 'folder':
            # sync all exported files and folders from the export with the ftp target directory
            rclone_response = rclone_sync_to_ftp(parsed_opts)

        elif parsed_opts.transport_packer in ['zip', 'tar.gz']:
            # copy the exported archive files from the export to the ftp target directory
            rclone_response = rclone_copyurl_to_ftp(parsed_opts)

        else:
            raise Exception('unknown packer {}'.format(parsed_opts.transport_packer))

        export_response['_state'] = 'done'
        export_response['_transport_log'] = []

        util.return_json_body(export_response)

    except util.CommandlineErrorException as e:
        print((str(e)))
        util.return_error('rclone_error', str(e))
    except Exception as e:
        print((str(e)))
        util.return_error('internal', str(e))
