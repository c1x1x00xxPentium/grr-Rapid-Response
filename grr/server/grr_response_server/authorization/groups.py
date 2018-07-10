#!/usr/bin/env python
"""Group authorization checking."""


import logging

from grr.core.grr_response_core import config
from grr.core.grr_response_core.lib import registry


class GroupAccessManager(object):
  __metaclass__ = registry.MetaclassRegistry

  __abstract = True  # pylint: disable=g-bad-name

  def AuthorizeGroup(self, group, subject):
    raise NotImplementedError()

  def MemberOfAuthorizedGroup(self, unused_username, unused_subject):
    raise NotImplementedError()


class NoGroupAccess(GroupAccessManager):
  """Placeholder class for enabling group ACLs.

  By default GRR doesn't have the concept of groups. To add it, override this
  class with a module in lib/local/groups.py that inherits from the same
  superclass. This class should be able to check group membership in whatever
  system you use: LDAP/AD/etc.
  """

  def AuthorizeGroup(self, group, subject):
    raise NotImplementedError("Replace this class to use group authorizations.")

  def MemberOfAuthorizedGroup(self, unused_username, unused_subject):
    return False


def CreateGroupAccessManager():
  group_mgr_cls = config.CONFIG["ACL.group_access_manager_class"]
  logging.debug("Using group access manager: %s", group_mgr_cls)
  return GroupAccessManager.classes[group_mgr_cls]()
