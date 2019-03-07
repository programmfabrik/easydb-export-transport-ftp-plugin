import ftplib
import os
import paramiko


def easydb_server_start(easydb_context):
    logger = easydb_context.get_logger('transport.ftp')
    logger.debug('initialize FTP plugin')

    easydb_context.register_callback('export_transport', {
        'transport_type': 'ftp',
        'callback': 'transport_ftp',
    })


def transport_ftp(easydb_context, protocol=None):
    logger = easydb_context.get_logger('transport.ftp')

    exp = easydb_context.get_exporter()

    transport = exp.getCurrentTransport()
    if not transport:
        raise Exception("failed to get current transport")

    opts = transport.get('options', {})
    if not 'server' in opts:
        logger.warn("no ftp host found")
        return

    server = opts.get('server')

    if server.startswith('ftp://'):
        FTP(easydb_context, opts, protocol).upload_files_from_export(exp)

    elif server.startswith('sftp://'):
        SFTP(easydb_context, opts, protocol).upload_files_from_export(exp)

    else:
        logger.warn("unknown protocol for host '%s'" % server)


class SFTP(object):

    def __init__(self, easydb_context, opts, protocol=None):
        self.logger = easydb_context.get_logger('transport.upload.sftp')
        self.protocol = protocol
        self.server = opts.get('server').split('://')[-1]
        self.login = opts.get('login')
        self.password = opts.get('password')
        self.basedir = opts.get('directory', '')


    def file_uploaded(self, bytes_transferred, bytes_total):
        self.logger.debug("put file progress: %s/%s bytes" % (bytes_transferred, bytes_total))
        self.bytes_total = bytes_total


    def upload_files_from_export(self, exp):

        self.logger.debug("SFTP server=%s login=%s" % (self.server, self.login))

        try:

            transport = paramiko.Transport((self.server, 22))
            transport.connect(None, self.login, self.password)

            sftp = paramiko.SFTPClient.from_transport(transport)
            self.logger.debug("successful connection to SFTP server")

            for fo in exp.getFiles():

                current_dir = sftp.getcwd()
                filepath = fo['path']

                local_file = os.path.join(os.path.abspath(exp.getFilesPath()), filepath)
                if not (os.path.exists(local_file) and os.path.isfile(local_file)):
                    self.logger.warn("export file '%s' does not exist -> skip" % local_file)
                    continue

                destination = os.path.join(self.basedir, os.path.dirname(filepath)).rstrip(os.sep)
                if not destination:
                    self.logger.warn("could not determine destination for file '%s' -> skip" % local_file)
                    continue

                for dnpart in destination.split(os.sep):
                    if not len(dnpart):
                        continue

                    path_exists = False
                    for d in sftp.listdir():
                        if d == dnpart:
                            path_exists = True
                            break

                    if not path_exists:
                        try:
                            sftp.mkdir(dnpart)
                        except Exception as e:
                            _err_str = "could not create sub directory '%s' (%s)" % (dnpart, str(e))
                            self.logger.warn(_err_str)
                            raise Exception(_err_str)

                    sftp.chdir(dnpart)

                self.bytes_total = None
                sftp.put(local_file, os.path.basename(filepath), callback=self.file_uploaded, confirm=True)
                if self.bytes_total:
                    self.logger.debug("put file '%s' as '%s' successfully (%s bytes)"
                        % (local_file, os.path.join(destination, os.path.basename(local_file)), self.bytes_total))

                if self.protocol:
                    self.protocol.add_notice("stored %s on SFTP server %s" % (local_file, self.server))

                if fo.get('eas_id'):
                    export_log_event(exp, fo)

                sftp.chdir(current_dir)

        except Exception as e:
            _err_str = "SFTP error (%s): %s" % (
                e.__class__.__name__,
                e)
            self.logger.warn(_err_str)
            if self.protocol:
                self.protocol.add_warning(_err_str)


class FTP(object):

    def __init__(self, easydb_context, opts, protocol=None):
        self.logger = easydb_context.get_logger('transport.upload.ftp')
        self.protocol = protocol
        self.server = opts.get('server')
        self.login = opts.get('login')
        self.password = opts.get('password')
        self.basedir = opts.get('directory', '')


    def upload_files_from_export(self, exp):

        self.logger.debug("FTP server=%s login=%s" % (self.server, self.login))

        try:
            ftp = ftplib.FTP(self.server, self.login, self.password)

            #ftp.set_debuglevel(1)

            # features = map(lambda x: x.strip(), ftp.sendcmd('FEAT').splitlines())
            # has_utf8 = 'UTF8' in features

            self.logger.debug("basedir='%s'" % self.basedir)

            bp = exp.getFilesPath()
            for fo in exp.getFiles():
                current_dir = ftp.pwd()
                rfn = fo['path']
                dn = os.path.join(self.basedir, os.path.dirname(rfn)).rstrip(os.sep)
                self.logger.debug("transport file '%s'" % dn)
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
                                    self.logger.warn('FTP error when trying to create directory: %s' % e.args[0])
                        ftp.cwd(dnpart)

                ftp.storbinary("STOR %s" % os.path.basename(rfn), open(os.path.join(bp, rfn)))
                self.logger.debug("stored %s on FTP server %s" % (rfn, self.server))

                if self.protocol:
                    self.protocol.add_notice("stored %s on FTP server %s" % (rfn, self.server))

                if fo.get('eas_id'):
                    export_log_event(exp, fo)

                ftp.cwd(current_dir)

        except ftplib.all_errors as e:
            _err_str = "FTP error (%s.%s): %s" % (
                e.__module__,
                e.__class__.__name__,
                e)
            self.logger.warn(_err_str)
            if self.protocol:
                self.protocol.add_warning(_err_str)


def export_log_event(exp, fo):
    exp.logEvent({
        'name': exp.isScheduled() and
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

