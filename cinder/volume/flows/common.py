#    Copyright (C) 2013 Yahoo! Inc. All Rights Reserved.
#    Copyright (c) 2013 OpenStack Foundation
#    Copyright 2010 United States Government as represented by the
#    Administrator of the National Aeronautics and Space Administration.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import six

from cinder import exception
from cinder.i18n import _LE
from cinder.openstack.common import log as logging

LOG = logging.getLogger(__name__)

# When a volume errors out we have the ability to save a piece of the exception
# that caused said failure, but we don't want to save the whole message since
# that could be very large, just save up to this number of characters.
REASON_LENGTH = 128


def make_pretty_name(method):
    """Makes a pretty name for a function/method."""
    meth_pieces = [method.__name__]
    # If its an instance method attempt to tack on the class name
    if hasattr(method, '__self__') and method.__self__ is not None:
        try:
            meth_pieces.insert(0, method.__self__.__class__.__name__)
        except AttributeError:
            pass
    return ".".join(meth_pieces)


def restore_source_status(context, db, volume_spec):
    # NOTE(harlowja): Only if the type of the volume that was being created is
    # the source volume type should we try to reset the source volume status
    # back to its original value.
    if not volume_spec or volume_spec.get('type') != 'source_vol':
        return
    source_volid = volume_spec['source_volid']
    source_status = volume_spec['source_volstatus']
    try:
        LOG.debug('Restoring source %(source_volid)s status to %(status)s' %
                  {'status': source_status, 'source_volid': source_volid})
        db.volume_update(context, source_volid, {'status': source_status})
    except exception.CinderException:
        # NOTE(harlowja): Don't let this cause further exceptions since this is
        # a non-critical failure.
        LOG.exception(_LE("Failed setting source "
                          "volume %(source_volid)s back to"
                          " its initial %(source_status)s status") %
                      {'source_status': source_status,
                       'source_volid': source_volid})


def error_out_volume(context, db, volume_id, reason=None):

    def _clean_reason(reason):
        if reason is None:
            return '???'
        reason = six.text_type(reason)
        if len(reason) <= REASON_LENGTH:
            return reason
        else:
            return reason[0:REASON_LENGTH] + '...'

    update = {
        'status': 'error',
    }
    reason = _clean_reason(reason)
    # TODO(harlowja): re-enable when we can support this in the database.
    # if reason:
    #     status['details'] = reason
    try:
        LOG.debug('Updating volume: %(volume_id)s with %(update)s'
                  ' due to: %(reason)s' % {'volume_id': volume_id,
                                           'reason': reason,
                                           'update': update})
        db.volume_update(context, volume_id, update)
    except exception.CinderException:
        # Don't let this cause further exceptions.
        LOG.exception(_LE("Failed updating volume %(volume_id)s with"
                          " %(update)s") % {'volume_id': volume_id,
                                            'update': update})
