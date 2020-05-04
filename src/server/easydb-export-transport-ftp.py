import ftplib
import os
import paramiko
import json


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

    if 'packer' in transport and transport['packer'] is not None:
        logger.debug('transport packer: {}'.format(transport['packer']))

        files_dir = exp.getFilesPath() + '/../tmp/'
        logger.debug('transport files dir: {}'.format(files_dir))

        filelist = []
        filetype_blacklist = ['.xsl', '.xslt']
        try:
            for dirpath, dirnames, filenames in os.walk(files_dir):
                for f in filenames:
                    skip = False
                    for fe in filetype_blacklist:
                        if f.endswith(fe):
                            skip = True
                            break
                    if skip:
                        continue
                    filelist.append({
                        'path': f
                    })
                break
        except Exception as e:
            logger.debug('could not get transport files list: {}'.format(str(e)))

        logger.debug('transport files list: {}'.format(json.dumps(filelist, indent=4)))
    else:
        files_dir = exp.getFilesPath()
        logger.debug('transport files dir: {}'.format(files_dir))
        filelist = exp.getFiles()
        logger.debug('transport files list: {}'.format(json.dumps(filelist, indent=4)))

    if server.startswith('ftp://') or server.startswith('ftps://'):
        FTP(easydb_context, opts, server.startswith('ftps://'), protocol).upload_files_from_export(exp, files_dir, filelist)

    elif server.startswith('sftp://'):
        SFTP(easydb_context, opts, protocol).upload_files_from_export(exp, files_dir, filelist)

    else:
        logger.warn("unknown protocol for host '%s'" % server)


class SFTP(object):

    def __init__(self, easydb_context, opts, protocol=None):
        self.logger = easydb_context.get_logger('transport.upload.sftp')
        self.protocol = protocol
        self.server = opts.get('server').split('://')[-1]
        while self.server.endswith('/'):
            self.server = self.server[:-1]
        self.login = opts.get('login')
        self.password = opts.get('password')
        self.basedir = opts.get('directory', '')


    def file_uploaded(self, bytes_transferred, bytes_total):
        self.logger.debug("put file progress: %s/%s bytes" % (bytes_transferred, bytes_total))
        self.bytes_total = bytes_total

    def upload_files_from_export(self, exp, files_dir, filelist):
        self.logger.debug("SFTP server=%s login=%s" % (self.server, self.login))

        try:

            transport = paramiko.Transport((self.server, 22))
            transport.connect(None, self.login, self.password)

            sftp = paramiko.SFTPClient.from_transport(transport)
            self.logger.debug("successful connection to SFTP server")

            for fo in filelist:

                current_dir = sftp.getcwd()
                filepath = fo['path']
                local_file = os.path.join(os.path.abspath(files_dir), filepath)
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
                    store_success_msg = "stored file '%s' as '%s' successfully on SFTP server %s (%s bytes)" % (
                        local_file, os.path.join(destination, os.path.basename(local_file)), self.server, self.bytes_total)
                else:
                    store_success_msg = "stored file '%s' as '%s' successfully on SFTP server %s" % (
                        local_file, os.path.join(destination, os.path.basename(local_file)), self.server)
                self.logger.debug(store_success_msg)

                if self.protocol:
                    self.protocol.add_notice(store_success_msg)

                if fo.get('eas_id'):
                    export_log_event(exp, fo)

                sftp.chdir(current_dir)

        except Exception as e:
            _err_str = "SFTP error (%s): %s" % (e.__class__.__name__, e)
            self.logger.warn(_err_str)
            if self.protocol:
                self.protocol.add_warning(_err_str)


class FTP(object):

    def __init__(self, easydb_context, opts, use_ftp_tls, protocol=None):
        self.logger = easydb_context.get_logger('transport.upload.ftps') if use_ftp_tls else easydb_context.get_logger('transport.upload.ftp')
        self.protocol = protocol
        self.server = opts.get('server').split('://')[-1]
        while self.server.endswith('/'):
            self.server = self.server[:-1]
        self.login = opts.get('login')
        self.password = opts.get('password')
        self.basedir = opts.get('directory', '')
        self.use_ftp_tls = use_ftp_tls
        self.server_protocol_str = 'FTPS' if use_ftp_tls else 'FTP'

    def upload_files_from_export(self, exp, files_dir, filelist):

        self.logger.debug("%s server=%s login=%s" % (self.server_protocol_str, self.server, self.login))

        try:
            if self.use_ftp_tls:
                ftp = ftplib.FTP_TLS(host=self.server, user=self.login, passwd=self.password)
            else:
                ftp = ftplib.FTP(host=self.server, user=self.login, passwd=self.password)

            # ftp.set_debuglevel(1)

            self.logger.debug("basedir='%s'" % self.basedir)

            for fo in filelist:
                current_dir = ftp.pwd()
                rfn = fo['path']
                local_file = os.path.join(os.path.abspath(files_dir), rfn)
                dn = os.path.join(self.basedir, os.path.dirname(rfn)).rstrip(os.sep)
                self.logger.debug("put file '%s'" % rfn)
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
                                    self.logger.warn('%s error when trying to create directory: %s' % (self.server_protocol_str, e.args[0]))
                        ftp.cwd(dnpart)

                ftp.storbinary("STOR %s" % os.path.basename(rfn), open(local_file))
                store_success_msg = "stored %s as %s on %s server %s" % (rfn, os.path.join(dn, os.path.basename(rfn)), self.server_protocol_str, self.server)
                self.logger.debug(store_success_msg)

                if self.protocol:
                    self.protocol.add_notice(store_success_msg)

                if fo.get('eas_id'):
                    export_log_event(exp, fo)

                ftp.cwd(current_dir)

        except ftplib.all_errors as e:
            _err_str = "%s error (%s.%s): %s" % (self.server_protocol_str, e.__module__, e.__class__.__name__, e)
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

