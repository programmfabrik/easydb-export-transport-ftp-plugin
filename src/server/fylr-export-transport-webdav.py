#!/bin/python


import sys
import json
from shared import util
import fylr_lib_plugin_python3.util as fylr_util


def rclone_sync_to_webdav(
    opts: util.PluginInfoJson,
) -> tuple[int, list[str], list[str]]:
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

    return util.run_rclone_command(
        parameters,
        util.rclone_log_level(opts.rclone_log_debug),
    )


def rclone_copyurl_to_webdav(
    opts: util.PluginInfoJson,
) -> tuple[int, list[str], list[str]]:
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

    return util.run_rclone_command(
        parameters,
        util.rclone_log_level(opts.rclone_log_debug),
    )


if __name__ == '__main__':

    try:
        # read export data from stdin
        stdin_json = util.read_json_from_stdin()

        # read %info.json% (needs to be given as the first argument)
        info_json = json.loads(sys.argv[1])

        parsed_opts = util.PluginInfoJson('webdav', info_json, stdin_json)
        export_response = parsed_opts.export

        # depending on the packer, decide which rclone method to use
        if (
            parsed_opts.transport_packer is None
            or parsed_opts.transport_packer == 'folder'
        ):
            # sync all exported files and folders from the export with the webdav target directory
            exit_code, rclone_stdout, rclone_stderr = rclone_sync_to_webdav(parsed_opts)

        elif parsed_opts.transport_packer in ['zip', 'tar.gz']:
            # copy the exported archive files from the export to the webdav target directory
            exit_code, rclone_stdout, rclone_stderr = rclone_copyurl_to_webdav(
                parsed_opts
            )

        else:
            raise Exception(f'unknown packer {parsed_opts.transport_packer}')

        util.return_json_body(
            util.format_export_response(
                export_response,
                exit_code,
                rclone_stdout,
                rclone_stderr,
            )
        )

    except Exception as e:
        util.return_json_body(
            {
                '_state': 'failed',
                '_transport_log': fylr_util.get_exception_traceback(e),
            }
        )
