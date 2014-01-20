#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=utf8 :

# Based loosely on http://code.activestate.com/recipes/577936-simple-curses-based-mysql-top/

# Copyright 2014 Gerald Combs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import curses
import json
import locale
import os
import requests
import sys
import time

try:
    from urllib import urlparse
except:
    import urlparse

col_names = {
    'change_id': 'Chg ID',
    'change_num': 'Chg #',
    'deletions': '-',
    'insertions': '+',
    'owner': 'Owner',
    'subject': 'Subject'
}

class GerritServer:
    '''Gerrit server information'''
    url = None
    hostname = 'Unknown'
    version = 'Unknown'
    changes = []
    change_digits = 1
    projects = {}

    __headers = { 'User-Agent': 'gerrit-top.py' }

    def __init__(self, url):
        self.url = url

    def update(self, max_changes = 50):
        '''Fetches information from the server'''
        if self.url is None: return

        # Version
        try:
            ver_url = '{}/config/server/version'.format(self.url)
            resp = requests.get(ver_url, headers = self.__headers)
            # https://gerrit-review.googlesource.com/Documentation/rest-api.html#output
            rest_version = json.loads(resp.text[resp.text.index('\n'):])
            if len(rest_version) > 0:
                self.version = rest_version
        except:
            pass

        # Hostname
        try:
            parts = urlparse.urlsplit(self.url)
            self.hostname = parts.hostname
        except:
            pass
        
        # Projects
        try:
            self.projects = {}
            proj_url = '{}/projects/'.format(self.url)
            resp = requests.get(proj_url, headers = self.__headers)
            rest_projects = json.loads(resp.text[resp.text.index('\n'):])
            self.projects = rest_projects
        except:
            pass

        # Changes
        try:
            self.changes = []
            insertions = '-'
            deletions = '-'
            changes_url = '{}/changes/?q=status:open&n={}'.format(self.url, max_changes)
            resp = requests.get(changes_url, headers = self.__headers)
            rest_changes = json.loads(resp.text[resp.text.index('\n'):])
            for chg in rest_changes:
                if chg.has_key('insertions') and chg.has_key('deletions'):
                    insertions = chg['insertions']
                    deletions = chg['deletions']
                self.changes.append({
                    'change_num': chg['_number'],
                    'owner': chg['owner']['name'],
                    'change_id': chg['change_id'],
                    'subject': chg['subject'],
                    'insertions': insertions,
                    'deletions': deletions,
                    })
        except:
            raise
            pass
        

def add_row(scr, row, line, attr = 0):
    width = scr.getmaxyx()[1]
    encoding = locale.getpreferredencoding()

    scr.addstr(row, 0, line.encode(encoding)[0:width], attr)


def refresh_screen(scr, gerrit_server):
    (height, width) = scr.getmaxyx()
    while 1:
        try:
            gerrit_server.update(height)
            row = 0

            project_count = len(gerrit_server.projects.keys())
            heading1 = u'{} Gerrit {}, {}, {} project{}'.format(
                time.strftime('%H:%M:%S'),
                gerrit_server.version,
                gerrit_server.hostname,
                project_count,
                '' if project_count == 1 else 's'
                )
            add_row(scr, row, heading1)
            row += 1

            #heading2 = '{} '
            #add_row(scr, row, 'Version: {} from {:20.20}'.format())
            #row += 1

            row += 1
            col_w = {
                'cnum_w': 6,
                'own_w': 9,
                'cid_w': 7,
                'ins_w': 4,
                'del_w': 4,
                'subj_w': width
            }
            col_format = str(u'{{change_num:>{cnum_w}}}'
            ' {{owner:{own_w}.{own_w}}}'
            ' {{change_id:{cid_w}.{cid_w}}}'
            ' {{insertions:>{ins_w}.{ins_w}}}'
            ' {{deletions:>{del_w}.{del_w}}}'
            ' {{subject:<{subj_w}.{subj_w}}}').format(**col_w)

            col_str = col_format.format(**col_names)
            add_row(scr, row, col_str, curses.A_BOLD|curses.A_REVERSE)

            row += 1

            if len(gerrit_server.changes) > 0:
                for change in gerrit_server.changes:
                    col_str = col_format.format(**change)
                    try:
                        add_row(scr, row, col_str)
                    except:
                        break
                    row += 1
            else:
                add_row(scr, row, 'No changes')

            scr.move(height - 2, width - 2)
            scr.refresh()
            time.sleep(5)
            scr.erase()
        except KeyboardInterrupt:
            sys.exit(-1)

if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, '')

    try:
        pass
    except IndexError:
        print 'Usage: %s <gerrit_url>'.format(os.path.basename(sys.argv[0]))
        sys.exit(-1)

    gerrit_server = GerritServer(sys.argv[1])
    curses.wrapper(refresh_screen, gerrit_server)

