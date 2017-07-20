# coding=utf-8
#

import os
import platform
import subprocess
from copy import deepcopy


class Command(object):
    def __init__(self, cmd, workdir=''):
        self.cmd = cmd
        self.workdir = workdir
        self.env = deepcopy(os.environ)
        if platform.system() == 'Linux':
            self.env['PATH'] = (self.env['PATH'] +
                                ':/usr/sbin:/sbin:/usr/bin:/bin:/usr/local/bin:/usr/local/sbin')

    def execute(self, stdin=None, join=True):
        if os.path.isdir(self.workdir):
            os.chdir(self.workdir)
        child = subprocess.Popen(self.cmd,
                                 shell=True,
                                 stdin=stdin,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 bufsize=1024*1024,
                                 env=self.env)
        if not join:
            return child
        return self.join(child)

    def pipe(self, other, join=True):
        child = self.execute(join=False)
        return other.execute(stdin=child.stdout, join=join)

    def __or__(self, other):
        return self.pipe(other)

    @classmethod
    def join(cls, child, errmsg='', up=True):
        data = child.communicate()
        try:
            data = [d.decode('utf-8') for d in data]
        except UnicodeDecodeError:
            data = [d.decode('gbk') for d in data]
        data.append(errmsg)
        if child.poll() != 0:
            assert not up, Exception(' '.join(data).strip())
        return data[0].strip()

