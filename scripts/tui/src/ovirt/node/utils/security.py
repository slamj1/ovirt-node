#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# security.py - Copyright (C) 2012 Red Hat, Inc.
# Written by Fabian Deutsch <fabiand@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.
from ovirt.node import base, valid, utils
import process
import os.path
import PAM as _PAM

"""
Some convenience functions related to security
"""


class Passwd(base.Base):
    def set_password(self, username, password):
        import ovirtnode.password as opasswd
        opasswd.set_password(password, username)


class Ssh(base.Base):
    def __init__(self):
        super(Ssh, self).__init__()

    def __update_profile(self, rng_num_bytes, disable_aes):
        import ovirtnode.ovirtfunctions as ofunc
        additional_lines = []
        ofunc.unmount_config("/etc/profile")

        process.system("sed -i '/OPENSSL_DISABLE_AES_NI/d' /etc/profile")
        if disable_aes:
            additional_lines += ["export OPENSSL_DISABLE_AES_NI=1"]

        process.system("sed -i '/SSH_USE_STRONG_RNG/d' /etc/profile")
        if rng_num_bytes:
            additional_lines += ["export SSH_USE_STRONG_RNG=%s" %
                                 rng_num_bytes]

        if additional_lines:
            self.logger.debug("Updating /etc/profile")
            with open("/etc/profile", "a") as f:
                lines = "\n" + "\n".join(additional_lines)
                f.write(lines)
            ofunc.ovirt_store_config("/etc/profile")

            self.restart()

    def disable_aesni(self, disable=None):
        """Set/Get AES NI for OpenSSL
        Args:
            enable: True or False
        Returns:
            The status of aes_ni
        """
        import ovirtnode.ovirtfunctions as ofunc
        rng, aes = ofunc.rng_status()
        if disable in [True, False]:
            self.__update_profile(rng, disable)
        else:
            self.logger.warning("Unknown value for AES NI: %s" % disable)
        return ofunc.rng_status()[1]  # FIXME should rurn bool
        # and does it return disable_aes_ni?

    def strong_rng(self, num_bytes=None):
        import ovirtnode.ovirtfunctions as ofunc
        rng, aes = ofunc.rng_status()
        if valid.Number(range=[0, None]).validate(num_bytes):
            self.__update_profile(num_bytes, aes)
        elif num_bytes is None:
            pass
        else:
            self.logger.warning("Unknown value for RNG num bytes: " +
                                "%s" % num_bytes)
        return ofunc.rng_status()[0]

    def restart(self):
        self.logger.debug("Restarting SSH")
        process.system("service sshd restart &>/dev/null")

    def password_authentication(self, enable=None):
        augpath = "/files/etc/ssh/sshd_config/PasswordAuthentication"
        aug = utils.AugeasWrapper()
        if enable in [True, False]:
            import ovirtnode.ovirtfunctions as ofunc
            value = "yes" if enable else "no"
            self.logger.debug("Setting SSH PasswordAuthentication to " +
                              "%s" % value)
            aug.set(augpath, value)
            ofunc.ovirt_store_config("/etc/ssh/sshd_config")
            self.restart()
        return aug.get(augpath)

    def get_hostkey(self, variant="rsa"):
        fn_hostkey = "/etc/ssh/ssh_host_%s_key.pub" % variant
        if not os.path.exists(fn_hostkey):
            raise Exception("SSH hostkey does not yet exist.")

        with open(fn_hostkey) as hkf:
            hostkey = hkf.read()

        hostkey_fp_cmd = "ssh-keygen -l -f '%s'" % fn_hostkey
        stdout = process.pipe(hostkey_fp_cmd, without_retval=True)
        fingerprint = stdout.strip().split(" ")[1]
        return (fingerprint, hostkey)


class PAM(base.Base):
    def _pam_conv(self, auth, query_list):
        resp = []
        for i in range(len(query_list)):
            resp.append((self._password, 0))
        return resp

    def authenticate(self, username, password):
        is_authenticated = False
        auth = _PAM.pam()
        auth.start("passwd")
        auth.set_item(_PAM.PAM_USER, username)
        self._password = password
        auth.set_item(_PAM.PAM_CONV, lambda a, q: self._pam_conv(a, q))
        try:
            auth.authenticate()
            is_authenticated = True
        except _PAM.error, (resp, code):
            self.logger.debug("Failed to authenticate: %s %s" % (resp, code))
        except Exception as e:
            self.logger.debug("Internal error: %s" % e)
        return is_authenticated