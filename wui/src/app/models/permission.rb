# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Scott Seago <sseago@redhat.com>
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

class Permission < ActiveRecord::Base
  belongs_to :pool

  validates_uniqueness_of :uid, :scope => "pool_id"

  ROLE_SUPER_ADMIN = "Super Admin"
  ROLE_ADMIN       = "Administrator"
  ROLE_USER        = "User"
  ROLE_MONITOR     = "Monitor"

  PRIV_PERM_SET    = "set_perms"
  PRIV_PERM_VIEW   = "view_perms"
  PRIV_MODIFY      = "modify"
  PRIV_VM_CONTROL  = "vm_control"
  PRIV_VIEW        = "view"

  ROLES = { ROLE_SUPER_ADMIN => [PRIV_VIEW, PRIV_VM_CONTROL, PRIV_MODIFY, 
                                 PRIV_PERM_VIEW, PRIV_PERM_SET],
            ROLE_ADMIN       => [PRIV_VIEW, PRIV_VM_CONTROL, PRIV_MODIFY],
            ROLE_USER        => [PRIV_VIEW, PRIV_VM_CONTROL],
            ROLE_MONITOR     => [PRIV_VIEW]}
 
  def self.invert_roles
    return_hash = {}
    ROLES.each do |role, privs|
      privs.each do |priv|
        priv_key = return_hash[priv]
        priv_key ||= []
        priv_key << role
        return_hash[priv] = priv_key
      end
    end
    return_hash
  end

  def name
    @account ||= Account.find("uid=#{uid}")

    @account.cn
  end

  PRIVILEGES = self.invert_roles

  def self.privileges_for_role(role)
    ROLES[role]
  end

  def self.roles_for_privilege(privilege)
    PRIVILEGES[privilege]
  end


end
