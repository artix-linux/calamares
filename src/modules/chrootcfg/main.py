#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <http://github.com/calamares> ===
#
#   Copyright 2016, Artoo <artoo@manjaro.org>
#   Copyright 2017, Philip Müller <philm@manjaro.org>
#   Copyright 2016, Artoo <artoo@cromnix.org>
#
#   Calamares is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Calamares is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Calamares. If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shutil
import subprocess
import libcalamares
from os.path import join

from libcalamares.utils import check_target_env_call, target_env_call, debug

ON_POSIX = os.name == 'posix'


class OperationTracker:
    """Tracks the overall operation process
    """

    def __init__(self):
        self.downloaded = 0
        self.installed = 0
        self.total = 0
        self.progress = 0.00

    def send_progress(self, counter, phase):
        """Send progress to calamares
        """

        for _ in range(phase):
            if self.total == 0:
                continue

            self.progress += (
                0.05 + (0.95 * (counter / self.total))
            ) / self.total
            debug("Progress: {}".format(self.progress))

        libcalamares.job.setprogress(self.progress)


class PacmanController:
    """Wrapper around pacman
    """

    def __init__(self, root):
        self.root = root
        self.operations = libcalamares.globalstorage.value(
            'packageOperations'
        )
        self.tracker = OperationTracker()
        self.keyrings = libcalamares.job.configuration.get('keyrings', [])

    def init_keyring(self):
        """Initializes pacman keyring
        """

        target_env_call(["pacman-key", "--init"])

    def populate_keyring(self):
        """Populates pacman keyring
        """

        target_env_call(["pacman-key", "--populate"] + self.keyrings)

    def parse_output(self, cmd):
        """Parses installation output
        """

        cal_env = os.environ.copy()
        cal_env["LC_ALL"] = "C"
        last = []
        phase = 0

        process = subprocess.Popen(
            cmd,
            env=cal_env,
            bufsize=1,
            stdout=subprocess.PIPE,
            close_fds=ON_POSIX
        )

        line = process.stdout.readline()
        while line:
            pkgs = re.findall(r'\((\d+)\)', line.decode())
            dl = re.findall(r'downloading\s+(.*).pkg.tar.xz', line.decode())
            inst = re.findall(r'installing(.*)\.\.\.', line.decode())

            if pkgs:
                self.tracker.total = (int(pkgs[0]))
                debug("Number of packages: {}".format(self.tracker.total))

            if dl:
                if dl != last:
                    self.tracker.downloaded += 1
                    phase = 1
                    debug("Downloading: {}".format(dl[0]))
                    debug("Downloaded packages: {}".format(
                        self.tracker.downloaded
                    ))
                    self.tracker.send_progress(self.tracker.downloaded, phase)

                last = dl
            elif inst:
                self.tracker.installed += 1
                phase = 2
                debug("Installing: {}".format(inst[0]))
                debug("Installed packages: {}".format(self.tracker.installed))
                self.tracker.send_progress(self.tracker.installed, phase)

            line = process.stdout.readline()

        if process.returncode != 0:
            return process.kill()

        return None

    def install(self, pkglist, local=False):
        """Install the given packagelist
        """

        cachedir = join(self.root, "var/cache/pacman/pkg")
        dbdir = join(self.root, "var/lib/pacman")

        args = 'pacman --noconfirm {} --cachedir {} --root {} --dbpath {} {}'
        cmd = args.format(
            '-U' if local else '-Sy', cachedir, self.root, dbdir,
            ' '.join(pkglist)
        )

        self.parse_output(cmd.split())

    def remove(self, pkglist):
        """Remove the given packagelist
        """

        check_target_env_call(
            'chroot {} pacman -Rs --noconfirm {}'.format(self.root, pkglist)
        )

    def run(self):
        """Run operations
        """

        pkgs = []
        for key in self.operations.keys():
            # append package to pkgs
            [pkgs.append(p['package']) for p in self.operations[key]]

            if key in ["install", "localinstall"]:
                self.install(pkgs, local=False if key == 'install' else True)
            elif key == "remove":
                self.tracker.total(len(pkgs))
                self.remove(pkgs)
            elif key == "try_install":
                self.install(pkgs)
            elif key == "try_remove":
                self.remove(pkgs)

        self.init_keyring()
        self.populate_keyring()


class ChrootController:
    """Chroot controller
    """

    def __init__(self):
        self.root = libcalamares.globalstorage.value('rootMountPoint')
        self.requirements = libcalamares.job.configuration.get(
            'requirements', []
        )

    def make_dirs(self):
        """Create needed directories
        """

        for target in self.requirements:
            dest = '{}{}'.format(self.root, target['name'])
            if not os.path.exists(dest):
                debug("Create: {}".format(dest))
                mod = int(target["mode"], 8)
                debug("Mode: {}".format(oct(mod)))
                os.makedirs(dest, mode=mod)

    def copy_file(self, file):
        """Copy the given file into root
        """

        orig = os.path.join("/", file)
        if os.path.exists(orig):
            shutil.copy2(orig, os.path.join(self.root, file))

    def prepare(self):
        """Prepare root environment
        """

        cal_umask = os.umask(0)
        self.make_dirs()
        os.umask(cal_umask)
        self.copy_file('etc/resolv.conf')

    def run(self):
        """Execute the controller
        """

        self.prepare()
        return PacmanController(self.root).run()


def run():
    """Download and install package selection
    """

    return ChrootController().run()
