#!/usr/bin/python
# coding=utf8

import unittest
from shared import util


class util_parse_ftp_url(unittest.TestCase):

    def test(self):

        for c in [
            # valid urls
            ('ftp://schema.easydb.de:21', 'ftp', 'schema.easydb.de', 21),
            ('ftp://schema.easydb.de', 'ftp', 'schema.easydb.de', 21),
            ('ftps://schema.easydb.de:21', 'ftps', 'schema.easydb.de', 21),
            ('ftps://schema.easydb.de', 'ftps', 'schema.easydb.de', 21),
            ('sftp://schema.easydb.de:21', 'sftp', 'schema.easydb.de', 21),
            ('sftp://schema.easydb.de', 'sftp', 'schema.easydb.de', 22),
            ('schema.easydb.de:21', 'ftp', 'schema.easydb.de', 21),
            ('schema.easydb.de', 'ftp', 'schema.easydb.de', 21),
            ('ftp://schema.easydb.de:21:21', 'ftp', 'schema.easydb.de', 21),
            # invalid urls or
            # invalid protocols, must be caught in main script
            ('xxx://schema.easydb.de:21', 'xxx', 'schema.easydb.de', 21),
            ('schema.easydb.de:21:21', 'schema.easydb.de', '21', None),
            ('ftp:/schema.easydb.de', None, None, None),
            ('ftp:///schema.easydb.de', None, None, None),
            ('ftp:///schema.easydb.de:21', None, None, None),
        ]:
            ftp_protocol, ftp_host, ftp_port = util.parse_ftp_url(c[0])
            print c[0], '->', ftp_protocol, ftp_host, ftp_port

            self.assertEqual(ftp_protocol, c[1])
            self.assertEqual(ftp_host, c[2])
            self.assertEqual(ftp_port, c[3])


if __name__ == '__main__':
    unittest.main()
