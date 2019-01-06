#!/usr/bin/env python

import ConfigParser
import csv
import os
import re
import socket
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from StringIO import StringIO
import struct
import sys
import urllib2
from zipfile import ZipFile

@Configuration(type='reporting')
class ASNGenCommand(GeneratingCommand):

    def generate(self):
        proxies = {'http': None, 'https': None}

        # Retrieve proxy settings, or skip.
        try:
            configparser = ConfigParser.ConfigParser()
            configparser.read(os.path.join(os.environ['SPLUNK_HOME'], 'etc/apps/TA-asngen/local/asngen.conf'))

            if configparser.has_section('proxies'):
                if configparser.has_option('proxies', 'http'):
                    if len(configparser.get('proxies', 'http')) > 0:
                        proxies['http'] = configparser.get('proxies', 'http')
                if configparser.has_option('proxies', 'https'):
                    if len(configparser.get('proxies', 'https')) > 0:
                        proxies['https'] = configparser.get('proxies', 'https')

        except:
            pass

        if proxies['http'] is not None or proxies['https'] is not None:
            proxy = urllib2.ProxyHandler(proxies)
            opener = urllib2.build_opener(proxy)
            urllib2.install_opener(opener)

        # Attempt to retrieve the file.
        try:
            url = urllib2.urlopen("https://geolite.maxmind.com/download/geoip/database/GeoLite2-ASN-CSV.zip")
        except Exception as ex:
            raise Exception(ex)

        # TODO: Is this necessary, given the above? Seems the previous try/except catches when it's a 404...
        if url.getcode() == 200:
            try:
                zipfile = ZipFile(StringIO(url.read()))
            except Exception as ex:
                raise Exception(ex)
        else:
            raise Exception("Received response: " + url.getcode())

        # Get the entries from each CSV file in the ZIP file.
        pate = r'^([0-9\.\/]+),(\d+),\"?(([^\"]+)|)\"?'
        for name in zipfile.namelist():
            if os.path.splitext(name)[1] == ".csv":
                with zipfile.open(name) as csvname:
                    csv_reader = csv.reader(csvname, delimiter=',', quotechar='"')
                    for row in csv_reader:
                        if re.match(pate, ",".join(row)) is not None:
                            yield {'ip': line[0], 'asn': line[1], 'autonomous_system': line[2].decode('utf-8', 'ignore')}

dispatch(ASNGenCommand, sys.argv, sys.stdin, sys.stdout, __name__)
