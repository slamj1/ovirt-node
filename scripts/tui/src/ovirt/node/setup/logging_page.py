#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# logging_page.py - Copyright (C) 2012 Red Hat, Inc.
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
"""
Configure Logging
"""

from ovirt.node import plugins, valid, ui, utils
from ovirt.node.config import defaults
from ovirt.node.plugins import Changeset


class Plugin(plugins.NodePlugin):
    _model = None
    _widgets = None

    def name(self):
        return "Logging"

    def rank(self):
        return 50

    def model(self):
        logrotate = defaults.Logrotate().retrieve()
        netconsole = defaults.Netconsole().retrieve()
        syslog = defaults.Syslog().retrieve()

        model = {}
        model["logrotate.max_size"] = logrotate["max_size"] or "1024"

        model["rsyslog.address"] = syslog["server"] or ""
        model["rsyslog.port"] = syslog["port"] or "514"

        model["netconsole.address"] = netconsole["server"] or ""
        model["netconsole.port"] = netconsole["port"] or "6666"

        return model

    def validators(self):
        """Validators validate the input on change and give UI feedback
        """
        return {
                "logrotate.max_size": valid.Number(range=[0, None]),
                "rsyslog.address": (valid.Empty() | valid.FQDNOrIPAddress()),
                "rsyslog.port": valid.Port(),
                "netconsole.address": (valid.Empty() |
                                       valid.FQDNOrIPAddress()),
                "netconsole.port": valid.Port(),
            }

    def ui_content(self):
        widgets = [
            ("header", ui.Header("Logging")),

            ("logrotate.max_size", ui.Entry("Logrotate Max Log " +
                                                 "Size (KB):")),

            ("divider[1]", ui.Divider()),
            ("rsyslog.header", ui.Label("RSyslog is an enhanced multi-" +
                                         "threaded syslogd")),
            ("rsyslog.address", ui.Entry("Server Address:")),
            ("rsyslog.port", ui.Entry("Server Port:")),

            ("divider[1]", ui.Divider()),
            ("netconsole.label", ui.Label(
                                    "Netconsole service allows a remote sys" +
                                    "log daemon to record printk() messages")),
            ("netconsole.address", ui.Entry("Server Address:")),
            ("netconsole.port", ui.Entry("Server Port:")),
        ]
        # Save it "locally" as a dict, for better accessability
        self._widgets = dict(widgets)

        page = ui.Page(widgets)
        return page

    def on_change(self, changes):
        pass

    def on_merge(self, effective_changes):
        self.logger.debug("Saving logging page")
        changes = Changeset(self.pending_changes(False))
        effective_model = Changeset(self.model())
        effective_model.update(effective_changes)

        self.logger.debug("Changes: %s" % changes)
        self.logger.debug("Effective Model: %s" % effective_model)

        txs = utils.Transaction("Updating logging related configuration")

        # If any logrotate key changed ...
        logrotate_keys = ["logrotate.max_size"]
        if changes.contains_any(logrotate_keys):
            # Get all logrotate values fomr the effective model
            model = defaults.Logrotate()
            # And update the defaults
            model.update(*effective_model.values_for(logrotate_keys))
            txs += model.transaction()

        rsyslog_keys = ["rsyslog.address", "rsyslog.port"]
        if changes.contains_any(rsyslog_keys):
            model = defaults.Syslog()
            model.update(*effective_model.values_for(rsyslog_keys))
            txs += model.transaction()

        netconsole_keys = ["netconsole.address", "netconsole.port"]
        if changes.contains_any(netconsole_keys):
            model = defaults.Netconsole()
            model.update(*effective_model.values_for(netconsole_keys))
            txs += model.transaction()

        progress_dialog = ui.TransactionProgressDialog(txs, self)
        progress_dialog.run()