#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <http://github.com/calamares> ===
#
#   Copyright 2014 - 2016, Philip Müller <philm@manjaro.org>
#   Copyright 2016, Artoo <artoo@manjaro.org>
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

import libcalamares

from os.path import join, exists
from libcalamares.utils import target_env_call


class ConfigController:
    def __init__(self):
        self.__root = libcalamares.globalstorage.value("rootMountPoint")

    @property
    def root(self):
        return self.__root

    def terminate(self, proc):
        target_env_call(['killall', '-9', proc])

    def run(self):

        # Workaround for pacman-key bug
        # FS#45351 https://bugs.archlinux.org/task/45351
        # We have to kill gpg-agent because if it stays
        # around we can't reliably unmount
        # the target partition.
        self.terminate('gpg-agent')

        # Update grub.cfg
        if exists(join(self.root, "usr/bin/update-grub")) \
                and libcalamares.globalstorage.value("bootLoader") is not None:
            target_env_call(["update-grub"])

        return None


def run():
    """ Misc postinstall configurations """

    config = ConfigController()

    return config.run()
