#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 Manfred Roiger <manfred.roiger@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''c2sg_bulk.py

A litte utility to assign computer(s) to JSS static computergroup(s).
Provide computer(s) and static group id(s) in a csv file and for each row
the computer is assigned to the corresponding static group.
Example content:

    mac00234,211
    mac00333,211
    mac01010,300

The first two Macs will be assigned to static group with id 211 and
the third Mac will be assigned to static group 300.

For example export a JSS advanced computer search, delete everything except
the computer names and add a column with static group id(s).
To prevent weird results or corruption of the JSS database.
we only use assignments to static computergroups.
'''

import requests
from requests.packages import urllib3
import json
import sys
import argparse
import getpass

# Set this flag to True to enable print output of various intermediate results
# If you run this script for the first time in your environment i recommend
# turning debug on. In this case we only read from JSS and output only the
# url for the put.
_debug = False

# The connection settings must be provided in a JSON file:
#   filename: ~//Library/Preferences/com.github.mvc2c.plist
#   dict with connection settings:
#       {
#           'jss_pass':'yourPassword',
#           'jss_user':'yourUser',
#           'jss_url':'https://yourJSSUrl:8443',
#           'jss_verify':0,
#           'jss_warn':1
#       }
#       if your JSS has a self signed certificate set jsss_verify to 0 and jss_warn to 1
#       jss_url must be the full url including https:// and port i.e. :8443
logged_in_user = getpass.getuser()
with open('/Users/' + logged_in_user + '/Library/Preferences/com.github.mvc2c.plist', 'r') as jss_settings:
    pl = json.load(jss_settings)

# Full url i.e. https://jssserver.domain.com:8443
jss_url = pl['jss_url']
# The user needs read access to computers and computergroups and update access to computergroups
jss_user = pl['jss_user']
jss_pass = pl['jss_pass']
# If set to True (1) we disable warnigs for self signed certificates
jss_warn = pl['jss_warn']
# If set to False (0) we disable ssl verify for self signed certificates
jss_verify = pl['jss_verify']

# Disable urrlib3 warnigs for JSS with self signed certificate
if jss_warn:
    urllib3.disable_warnings()

s = requests.Session()
s.auth = (jss_user, jss_pass)
s.headers.update({'Accept': 'application/json'})
s.verify = jss_verify

def get_computer(computer):
    '''Get full set of computer information that can be retrieved by computer name.'''
    s.headers.update({'Accept': 'application/json'})
    try:
        response = s.get(jss_url + '/JSSResource/computers/name/' + computer)
    except requests.exceptions.ProxyError:
        print('Cannot connect to ' + jss_url + ' ProxyError .. exiting')
        sys.exit(1)
    if response.status_code != requests.codes.ok:
        print("Search for " + computer + " failed with return code: " + str(response.status_code))
        return False
    else:
        return True

def get_software(gid, static_groups):
    '''Search for software in list of static computergrups.'''
    for value in static_groups:
        if gid in str(value):
            # ID matches one group return True
            return True
    # If nothing matches return False
    print('No such static group: ' + gid)
    return False

parser = argparse.ArgumentParser()
parser.add_argument('filename', help="CSV file with [computers,id] to assign.")
args = parser.parse_args()

# In ci_list we fetch all lines in an array
ci_list = []

if args.filename != None:
    try:
        with open(args.filename, 'r') as csv_file:
            for line in csv_file.readlines():
                ci_list.append(line.strip('\r\n'))
    except IOError:
        print('No such file or directory: ' + args.filname)
        sys.exit(1)

# Get all computergroups from jss
try:
    response = s.get(jss_url + '/JSSResource/computergroups')
except requests.exceptions.ProxyError:
    print('Cannot connect to ' + jss_url + ' ProxyError .. exiting')
    sys.exit(1)
if response.status_code != requests.codes.ok:
    print('Could not load computergroups, return code was: ' + str(response.status_code))

computergroups = json.loads(response.content)

# In static_groups we select all static groups from computegroups
static_groups = []
# Extract all static groups from computer groups, we only assign to static groups
for value in computergroups['computer_groups']:
    if value['is_smart'] == False:
        static_groups.append(value['id'])

for value in ci_list:
    # Excel files have ';' as separator
    if ';' in value:
        computer = value.split(';')[0]
        group = value.split(';')[1]
    # Normal csv should have ',' as seperator
    else:
        computer = value.split(',')[0]
        group = value.split(',')[1]
    if get_computer(computer) and get_software(group, static_groups):
        # Add  computer to selected static group
        # Change the header to xml as jss only accepts xml for put
        s.headers.update({'content-type': 'application/xml'})
        data = '<computer_group><computer_additions><computer><name>' + computer + '</name></computer></computer_additions></computer_group>'
        group_url = jss_url + '/JSSResource/computergroups/id/' + group
        if _debug:
            print (group_url)
            print (data)
        else:
            try:
                response = s.put(url=group_url, data=data)
            except requests.exceptions.ProxyError:
                print('Cannot connect to ' + jss_url + ' ProxyError .. exiting')
                sys.exit(1)
            if response.status_code == 201:
                print('Added ' + computer + ' to group with id: ' + str(group))
            else:
                print('Update for group ' + str(group) + ' failed with return code: ' + str(response.status_code))
                sys.exit(response.status_code)
    else:
        print('Skipping line: ' + str(value))