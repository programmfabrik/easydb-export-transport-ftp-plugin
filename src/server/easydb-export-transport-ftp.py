import ftplib
import os

def easydb_server_start(easydb_context):
    logger = easydb_context.get_logger('transport.ftp')
    logger.debug('initialize FTP plugin')

    easydb_context.register_callback('export_transport', {
        'transport_type': 'ftp',
        'callback': 'transport_ftp',
    })

def transport_ftp(easydb_context, protocol = None):
    logger = easydb_context.get_logger('transport.ftp')

    exp = easydb_context.get_exporter()

    transport = exp.getCurrentTransport()
    if not transport:
        raise Exception("failed to get current transport")

    opts = transport.get('options', {})

    try:
        ftp = ftplib.FTP(
            opts.get('server'),
            opts.get('login'),
            opts.get('password'))

        #ftp.set_debuglevel(1)

        features = map(lambda x: x.strip(), ftp.sendcmd('FEAT').splitlines())
        has_utf8 = 'UTF8' in features

        basedir = opts.get('directory', '')

        bp = exp.getFilesPath()
        for fo in exp.getFiles():
            current_dir = ftp.pwd()
            rfn = fo['path']
            dn = os.path.join(basedir, os.path.dirname(rfn)).rstrip(os.sep)
            if dn:
                for dnpart in dn.split(os.sep):
                    if not len(dnpart):
                        # empty start, absolute path
                        ftp.cwd("/")
                        continue
                    try:
                        ftp.mkd(dnpart)
                    except Exception, e:
                        # somewhat complicated to detect "file exists",
                        # RFC 959: '521-"/usr/dm/pathname" directory already exists;'
                        # ProFTPd: '550 S2@g_n_a_r_g: File exists'
                        if len(e.args) > 0:
                            if not 'exists' in e.args[0]:
                                logger.warn('FTP error when trying to create directory: %s' % e.args[0])
                    ftp.cwd(dnpart)

            ftp.storbinary("STOR %s" % os.path.basename(rfn), open(os.path.join(bp, rfn)))
            protocol.add_notice("stored %s on FTP server %s" % (rfn, opts.get('server')))

            if fo.get('eas_id'):
                exp.logEvent({
                    'name': exp.isScheduled() and \
                        'ASSET_EXPORT_TRANSPORT_COPY_SCHEDULED' or
                        'ASSET_EXPORT_TRANSPORT_COPY',
                    'pollable': False,
                    'base_type': 'asset',
                    'object_id': fo.get('eas_id'),
                    'event_info': {
                        'version': fo.get('eas_version'),
                        'class': fo.get('eas_fileclass'),
                        'system_object_id': fo.get('system_object_id'),
                    },
                })

            ftp.cwd(current_dir)
    except ftplib.all_errors as e:
        protocol.add_warning("FTP error (%s.%s): %s" % (
            e.__module__,
            e.__class__.__name__,
            e))

