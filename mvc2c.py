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
'''mvc2c.py

A litte utility to "move" software from one computer to another computer.
To prevent weird results or corruption of the JSS database
we only use assignments to static computer groups.
'''

import requests
from requests.packages import urllib3
import json
import sys
import argparse
import getpass

# Set this flag to True to enable print output of various intermediate results
_debug = True

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

jss_url = pl['jss_url']
jss_user = pl['jss_user']
jss_pass = pl['jss_pass']
jss_warn = pl['jss_warn'] # If set to True (1) we disable warnigs for self signed certificates
jss_verify = pl['jss_verify'] # If set to False (0) we disable ssl verify for self signed certificates

if jss_warn:
    urllib3.disable_warnings()

s = requests.Session()
s.auth = (jss_user, jss_pass)
s.headers.update({'Accept': 'application/json'})
s.verify = jss_verify

def get_computer(computer):
    '''Get full set of computer information that can be retrieved by computer name!'''
    try:
        response = s.get(jss_url + '/JSSResource/computers/name/' + computer)
    except requests.exceptions.ProxyError:
        print('Cannot connect to ' + jss_url + ' ProxyError .. exiting')
        sys.exit(1)
    if response.status_code != requests.codes.ok:
        print("Request " + computer + " by name failed with return code: " + str(response.status_code))
        sys.exit(response.status_code)
    else:
        content = json.loads(response.content)
        if _debug:
            print(content['computer']['general']['id'])
        return content

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--source", type=str,
                    help="Optional: Name of a source computer to read computergroup memberships.")
parser.add_argument("-d", "--destination", type=str,
                    help="Optional: Name of a destination computer that will be assigned to matching static computergroups.")
args = parser.parse_args()

if args.source != None:
    source_computer = args.source
else:
    source_computer = raw_input('Enter source computer: ')

if args.destination != None:
    dest_computer = args.destination
else:
    dest_computer = raw_input('Enter destination computer: ')

# We need the groups_accounts subset of the computer dictionary
groups_accounts = get_computer(source_computer)

# Just check if computer exists we don't need the content
get_computer(dest_computer)

# Extract the computer_group_memberships in a list
computer_group_memberships = groups_accounts['computer']['groups_accounts']['computer_group_memberships']
if _debug:
    print(json.dumps(computer_group_memberships, indent=2, sort_keys=True))

# Get all computer groups from jss
try:
    response = s.get(jss_url + '/JSSResource/computergroups')
except requests.exceptions.ProxyError:
    print('Cannot connect to ' + jss_url + ' ProxyError .. exiting')
    sys.exit(1)
if response.status_code != requests.codes.ok:
    print(response.status_code)

computergroups = json.loads(response.content)
if _debug:
    print(json.dumps(computergroups, indent=2, sort_keys=True))

static_groups = []

# Extract all static groups from computer groups, we only assign to static groups
for value in computergroups['computer_groups']:
    if value['is_smart'] == False:
        static_groups.append([value['id'], value['name']])

if _debug:
    print(static_groups)

group_overlap = []

# Search fpr matches of static groups in group memberships of source computer
for group in static_groups:
    if group[1] in computer_group_memberships:
        group_overlap.append(group[0])
        if _debug:
            print(group[1])

# Check if we have anything to do
if len(group_overlap) == 0:
    print(source_computer + ' has no mebership in static groups!')
    sys.exit(1)

# Add destination computer to all static groups the source computer is a member of
# Change the header to xml as jss only accepts xml
s.headers.update({'content-type': 'application/xml'})
data = '<computer_group><computer_additions><computer><name>' + dest_computer + '</name></computer></computer_additions></computer_group>'

for group in group_overlap:
    group_url = jss_url + '/JSSResource/computergroups/id/' + str(group)
    if _debug:
        print (group_url)
    else:
        try:
            response = s.put(url=group_url, data=data)
        except requests.exceptions.ProxyError:
            print('Cannot connect to ' + jss_url + ' ProxyError .. exiting')
            sys.exit(1)
        if response.status_code == 201:
            print('Added ' + dest_computer + ' to group with id: ' + str(group))
        else:
            print('Update for group ' + str(group) + ' failed with return code: ' + str(response.status_code))
            sys.exit(response.status_code)
