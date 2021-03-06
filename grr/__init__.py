#!/usr/bin/env python3
from __future__ import print_function, unicode_literals

import configparser
import json
import subprocess
import sys
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

if sys.version_info[0] == 2:
    input = raw_input  # noqa


class Grr:
    def __init__(self, debug=False):
        self._debug = debug
        self._username = None
        self._config = None

    def debug(self, text):
        if self._debug:
            self.out(text)

    def out(self, text):
        print(text)

    def shell_exec(self, args):
        self.debug('$ ' + ' '.join(args))
        return subprocess.check_output(args).decode()

    def run(self, *args):
        args = list(args)
        if args:
            action = args.pop(0)
        else:
            action = 'review'
        self.debug('action: {0}, args: {1}'.format(action, ' '.join(args)))
        if action == 'init':
            # grr init
            self.init_repo()
        elif action == 'fetch':
            # grr 12345
            # grr 12345:2
            self.fetch(args[0])
        elif action == 'pull':
            # grr pull
            # grr pull REL1_24
            self.pull(*args)
        elif action == 'checkout':
            # grr checkout
            # grr checkout REL1_24
            self.checkout(*args)
        elif action == 'review':
            # grr review REL1_24
            self.review(*args)
        elif not action:
            # grr
            self.review()
        else:
            # grr branch
            self.review(action)

    @property
    def config(self):
        if self._config is None:
            self.debug('Parsing .gitreview file...')
            config = configparser.ConfigParser()
            config.read('.gitreview')
            self._config = config['gerrit']
        return self._config

    def rest_api(self, query):
        self.debug('Making API request to: {query}'.format(query=query))
        req = urlopen('https://{host}/r/{query}'.format(host=self.config['host'], query=query))
        resp = req.read().decode()[4:]
        return json.loads(resp)

    @property
    def username(self):
        if self._username is None:
            try:
                username = self.shell_exec(['git', 'config', 'gitreview.username']).strip()
            except subprocess.CalledProcessError:
                username = input('Please enter your gerrit username: ').strip()
                self.shell_exec(['git', 'config', '--get', 'gitreview.username', username])
            self._username = username
        return self._username

    def checkout(self, branch='master'):
        self.shell_exec(['git', 'checkout', 'origin/{0}'.format(branch)])

    def pull(self, branch='master'):
        self.shell_exec(['git', 'fetch', 'origin'])
        self.checkout(branch)

    def review(self, branch='master'):
        self.init_repo()
        self.shell_exec(['git', 'push', 'gerrit', 'HEAD:refs/for/{0}'.format(branch)])

    def fetch(self, changeset):
        if ':' in changeset:
            change, patch = changeset.split(':', 1)
            fetch = {
                'url': 'https://{host}/r/{name}'.format(
                    host=self.config['host'],
                    name=self.config['project'].strip('.git')
                ),
                'ref': 'refs/changes/{0}/{1}/{2}'.format(change[-2:], change, patch)
            }
        else:
            change = changeset
            query = self.rest_api('changes/{0}?o=CURRENT_REVISION'.format(change))
            current_rev = query['current_revision']
            fetch = query['revisions'][current_rev]['fetch']['anonymous http']
        self.shell_exec(['git', 'fetch', fetch['url'], fetch['ref']])
        self.shell_exec(['git', 'checkout', 'FETCH_HEAD'])

    def init_repo(self):
        output = self.shell_exec(['git', 'remote'])
        if 'gerrit\n' in output:
            # Remote already setup
            return False
        remote = 'ssh://{username}@{host}:{port}/{project}'.format(username=self.username, **self.config)
        self.shell_exec(['git', 'remote', 'add', 'gerrit', remote])
        self.out('Added gerrit remote')
        commit_msg = '{username}@{host}:hooks/commit-msg'.format(username=self.username, **self.config)
        self.shell_exec(['scp', '-P' + self.config['port'], commit_msg, '.git/hooks/commit-msg'])
        self.out('Installed commit-msg hook')
        self.shell_exec(['git', 'checkout', 'origin/master', '-q'])


def main():
    args = sys.argv[1:]
    debug = '--debug' in args
    if debug:
        args.remove('--debug')
    g = Grr(debug=debug)
    g.run(*args)

if __name__ == '__main__':
    main()
