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

import libcalamares

from libcalamares.utils import target_env_call
from os.path import exists, join


class ServicesController:
    """This is the service controller
    """

    def __init__(self):
        self.root = libcalamares.globalstorage.value('rootMountPoint')
        self.services = libcalamares.job.configuration.get('services', [])

    def setExpression(self, pattern, file):
        """Sed the given file with the given pattern
        """

        target_env_call(["sed", "-e", pattern, "-i", file])

    def configure(self):
        """Configure the services
        """

        self.setExpression(
            's|^.*rc_shell=.*|rc_shell="/usr/bin/sulogin"|',
            "/etc/rc.conf"
        )
        self.setExpression(
            's|^.*rc_controller_cgroups=.*|rc_controller_cgroups="YES"|',
            "/etc/rc.conf"
        )
        exp = 's|^.*keymap=.*|keymap="{}"|'.format(
            libcalamares.globalstorage.value("keyboardLayout")
        )

        self.setExpression(exp, "/etc/conf.d/keymaps")
        for dm in libcalamares.globalstorage.value("displayManagers"):
            exp = 's|^.*DISPLAYMANAGER=.*|DISPLAYMANAGER="{}"|'.format(dm)
            self.setExpression(exp, "/etc/conf.d/xdm")

    def update(self, action, state):
        """Update init scripts
        """

        for svc in self.services[state]:
            if exists(self.root + "/etc/init.d/" + svc["name"]):
                target_env_call(
                    ["rc-update", action, svc["name"], svc["runlevel"]]
                )

    def run(self):
        """Run the controller
        """

        self.configure()
        for state in self.services.keys():
            if state == "enabled":
                self.update("add", "enabled")
            elif state == "disabled":
                self.update("del", "disabled")


def run():
    """Setup openrc services
    """

    return ServicesController().run()
