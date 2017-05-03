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
'''c2sg.py

A litte utility to assign a computer to a JSS static computergroup.
To prevent weird results or corruption of the JSS database.
we only use assignments to static computergroups.
'''

import requests
from requests.packages import urllib3
import json
import sys
import argparse
import getpass
from string import lower

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

'''
    Script can be started with three optional parameters:
    -c [computer]
    -s [software]
    -i [id of a static group]
'''
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--computer", type=str,
                    help="Optional: Name of a computer to add to static group.")
parser.add_argument("-s", "--software", type=str,
                    help="Optional: Name of a software a computer will be assigned to.")
parser.add_argument("-i", "--id", type=str,
                    help="Optional: Group ID of a software a computer will be assigned to. Ignored if -s is present.")
args = parser.parse_args()

# Computer name is fetched from args (-c) or read from input
if args.computer != None:
    computer = args.computer
else:
    computer = raw_input('Enter a computer name: ')

# Check if the computer exists in JSS. The function exits if the computer does not exist
# We don't need the content in this script
get_computer(computer)

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
# gid will be the list with static group ids the computer will be assigned to
# we append only strings to gid because we need strings for our put url
gid = []

# Extract all static groups from computer groups, we only assign to static groups
for value in computergroups['computer_groups']:
    if value['is_smart'] == False:
        static_groups.append([value['id'], value['name']])

# We allow to further narrow the computergroups by matching a software name
group_selection = []

# Check which software should be assigend either from args (-s) or read from input
if args.software != None:
    software = lower(args.software)
    for value in static_groups:
        if software in lower(value[1]):
            print('ID: %3d : %s' % (value[0], value[1]))
            group_selection.append(value)
    if len(group_selection) == 0:
        print('No software found that matches: ' + software)
        sys.exit(1)

# If no -s option was in args, there might be a -i option
# If an -s option is in args, we ignore the -i option
elif args.id != None:
    for value in static_groups:
        if args.id in str(value[0]):
            gid.append(args.id)
            break
    if len(gid) == 0:
        print('No software with ID: ' + str(args.id) + ' found .. exiting!')
        sys.exit(1)
else:
    software = raw_input('Please enter a software name or hit <Enter> for a complete list: ')
    if software != None:
        for value in static_groups:
            if lower(software) in lower(value[1]):
                print('ID: %3d : %s' % (value[0], value[1]))
                group_selection.append(value)
    else:
        for value in static_groups:
            print('ID: %3d : %s' % (value[0], value[1]))
            group_selection.append(value)

    if len(group_selection) == 0:
        print('Nothing selected .. exiting!')
        sys.exit(1)

# We are graceful and allow retries if an id was misspelled
spelling_wrong = False

# Skip additional prompt for ids if -i option was in args and no -s option
if len(gid) == 0:
    while True:
        if spelling_wrong:
            print(str(group_to_update) + ' not found please check spelling and try again!')
            spelling_wrong = False
        group_to_update = raw_input('Please enter the ID of a software you want to assign, hit <Enter> when finished: ')
        if group_to_update != '':
            for value in group_selection:
                if group_to_update in  str(value[0]):
                    spelling_wrong = False
                    gid.append(str(group_to_update))
                    break
            else:
                spelling_wrong = True
        else:
            break

# We should now have at least one id of a static group
if len(gid) == 0:
    print('Nothing selected .. exiting!')
    sys.exit(1)

# Add  computer to all selected static groups
# Change the header to xml as jss only accepts xml
s.headers.update({'content-type': 'application/xml'})
data = '<computer_group><computer_additions><computer><name>' + computer + '</name></computer></computer_additions></computer_group>'

for group in gid:
    group_url = jss_url + '/JSSResource/computergroups/id/' + group
    if _debug:
        print (group_url)
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