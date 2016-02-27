# -*- coding: utf-8 -*-

import csv
import pprint
from decimal import Decimal
from datetime import datetime, date
try:  # py3
    from io import StringIO
except ImportError:  # py2
    from StringIO import StringIO
from atomx.utils import _class_property
from atomx.exceptions import (
    NoSessionError,
    ModelNotFoundError,
    APIError,
    ReportNotReadyError,
    NoPandasInstalledError,
)

__all__ = ['AccountManager', 'Advertiser', 'Bidder', 'Browser',
           'CampaignDebugReason', 'Campaign', 'Category', 'ConnectionType',
           'ConversionPixel', 'Country', 'Creative', 'CreativeAttribute',
           'Datacenter', 'DeviceType', 'Domain', 'Fallback', 'Isp', 'Languages', 'Network',
           'OperatingSystem', 'Placement', 'PlacementType', 'Profile', 'Publisher', 'Reason',
           'Segment', 'SellerProfile', 'Site', 'Size', 'User', 'Visibility']


class AtomxModel(object):
    """A generic atomx model that the other models from :mod:`atomx.models` inherit from.

    :param int id: Optional model ID. Can also be passed in via `attributes` as `id`.
    :param atomx.Atomx session: The :class:`atomx.Atomx` session to use for the api requests.
    :param attributes: model attributes
    """
    def __init__(self, id=None, session=None, **attributes):
        for k, v in attributes.items():
            if k.endswith('_at'):
                try:
                    attributes[k] = datetime.strptime(v, '%Y-%m-%dT%H:%M:%S')
                except (ValueError, TypeError):
                    pass
            elif k == 'date':
                try:
                    attributes[k] = datetime.strptime(v, '%Y-%m-%d')
                except (ValueError, TypeError):
                    pass
        if id is not None:
            attributes['id'] = id

        super(AtomxModel, self).__setattr__('session', session)
        super(AtomxModel, self).__setattr__('_attributes', attributes)
        super(AtomxModel, self).__setattr__('_dirty', set())  # list of changed attributes

    def __getattr__(self, item):
        from .utils import get_attribute_model_name
        model_name = get_attribute_model_name(item)
        attr = self._attributes.get(item)
        # if requested attribute item is a valid model name and and int or
        # a list of integers, just delete the attribute so it gets
        # fetched from the api
        if model_name and (isinstance(attr, int) or
                           isinstance(attr, list) and len(attr) > 0 and
                           isinstance(attr[0], int)):
            del self._attributes[item]

        # if item not in model and session exists,
        # try to load model attribute from server if possible
        if not item.startswith('_') and item not in self._attributes and self.session:
            try:
                v = self.session.get(self.__class__._resource_name, self.id, item)
                self._attributes[item] = v
            except APIError as e:
                raise AttributeError(e)
        return self._attributes.get(item)

    def __setattr__(self, key, value):
        if self._attributes.get(key) != value:
            self._attributes[key] = value
            self._dirty.add(key)

    def __delattr__(self, item):
        if item in self._dirty:
            self._dirty.remove(item)

        self._attributes[item] = [] if isinstance(self._attributes[item], list) else None
        self._dirty.add(item)

    def __dir__(self):
        """Manually add dynamic attributes for autocomplete"""
        return dir(type(self)) + list(self.__dict__.keys()) + list(self._attributes.keys())

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, pprint.pformat(self.json))

    def __eq__(self, other):
        return self.id == getattr(other, 'id', 'INVALID')

    def __getstate__(self):  # for pickle dump
        return self._attributes

    def __setstate__(self, state):  # for pickle load
        self.__init__(**state)


    @_class_property
    def _resource_name(cls):
        from atomx.utils import model_name_to_rest
        return model_name_to_rest(cls.__name__)

    @property
    def _dirty_json(self):
        dirty = {}
        for attr in self._dirty:
            val = self._attributes[attr]
            if isinstance(val, datetime) or isinstance(val, date):
                dirty[attr] = val.isoformat()
            elif isinstance(val, Decimal):
                dirty[attr] = float(val)
            elif isinstance(val, set):
                dirty[attr] = list(val)
            else:
                dirty[attr] = val

        return dirty

    @property
    def json(self):
        """Returns the model attributes as :class:`dict`."""
        return self._attributes

    def create(self, session=None):
        """`POST` the model to the api and populates attributes with api response.

        :param session: The :class:`atomx.Atomx` session to use for the api call.
            (Optional if you specified a `session` at initialization)
        :return: ``self``
        :rtype: :class:`.AtomxModel`
        """
        session = session or self.session
        if not session:
            raise NoSessionError
        res = session.post(self._resource_name, json=self.json)
        self.__init__(session=session, **res)
        return self

    def update(self, session=None):
        """Alias for :meth:`.AtomxModel.save`."""
        return self.save(session)

    def save(self, session=None):
        """`PUT` the model to the api and update attributes with api response.

        :param session: The :class:`atomx.Atomx` session to use for the api call.
            (Optional if you specified a `session` at initialization)
        :return: ``self``
        :rtype: :class:`.AtomxModel`
        """
        session = session or self.session
        if not session:
            raise NoSessionError
        res = session.put(self._resource_name, self.id, json=self._dirty_json)
        self.__init__(session=session, **res)
        return self

    def delete(self, session=None):
        """Delete is currently not supported by the api.
        Set `state` to `INACTIVE` to deactivate it.
        """
        raise NotImplementedError("Delete is currently not supported by the api."
                                  "Set `state` to `INACTIVE` to deactivate it.")

    def reload(self, session=None):
        """Reload the model from the api and update attributes with the response.

        This is useful if you have not all attributes loaded like when you made
        an api request with the `attributes` parameter or you used :meth:`atomx.Atomx.search`.

        :param session: The :class:`atomx.Atomx` session to use for the api call.
            (Optional if you specified a `session` at initialization)
        :return: ``self``
        :rtype: :class:`.AtomxModel`
        """
        session = session or self.session
        if not session:
            raise NoSessionError
        if not hasattr(self, 'id'):
            raise ModelNotFoundError("Can't reload without 'id' parameter. "
                                     "Forgot to save() first?")
        res = session.get(self._resource_name, self.id)
        self.__init__(session=session, **res.json)
        return self

    def history(self, session=None, offset=0, limit=100, sort='date.asc'):
        """Show the changelog of the model.

        :param session: The :class:`atomx.Atomx` session to use for the api call.
            (Optional if you specified a `session` at initialization)
        :param int offset: Skip first ``offset`` history entries. (default: 0)
        :param int limit: Only return ``limit`` history entries. (default: 100)
        :param str sort: Sort by `date.asc` or `date.desc`. (default: 'date.asc')
        :return: `list` of `dict`s with `date`, `user` and the attributes that changed (`history`).
        :rtype: list
        """
        session = session or self.session
        if not session:
            raise NoSessionError
        if not hasattr(self, 'id'):
            raise ModelNotFoundError("Can't reload without 'id' parameter. "
                                     "Forgot to save() first?")
        res = session.get('history', self._resource_name, self.id,
                          offset=offset, limit=limit, sort=sort)
        return res


for m in __all__:
    locals()[m] = type(m, (AtomxModel,),
                       {'__doc__': ':class:`.AtomxModel` for {}'.format(m)})


class ScheduledReport(object):
    """A report scheduling object that you get back when registering a new scheduled report.
    See the `scheduling section in the atomx wiki
    <https://wiki.atomx.com/reporting#scheduling_reports>`_.
    """

    def __init__(self, id, session, name, emails, query, **kwargs):
        self.session = session
        self.id = id
        self.name = name
        self.emails = emails
        self.query = query

    def __repr__(self):
        return "ScheduledReport(id='{}', query={})".format(self.id, self.query)

    def __eq__(self, other):
        return self.id == getattr(other, 'id', 'INVALID')

    def save(self, session=None):
        """Update report `name` and `emails`"""

        session = session or self.session
        if not session:
            raise NoSessionError
        return session.put('report', self.id, {'name': self.name, 'emails': self.emails})

    def delete(self, session=None):
        """Delete scheduled report"""

        session = session or self.session
        if not session:
            raise NoSessionError
        return session.delete('report', self.id)


class Report(object):
    """Represents a `report` you get back from :meth:`atomx.Atomx.report`."""

    def __init__(self, id, session, query, fast, lines, error, link,
                 started, finished, is_ready, duration, name, **kwargs):
        self.session = session
        self.query = query
        self.fast = fast
        self.id = id
        self.lines = lines
        self.error = error
        self.link = link
        self.started = started
        self.finished = finished
        self.duration = duration
        self.name = name

        if is_ready:
            self._is_ready = is_ready

    def __repr__(self):
        return "Report(id='{}', is_ready={}, query={})".format(self.id, self.is_ready, self.query)

    def __eq__(self, other):
        return self.id == getattr(other, 'id', 'INVALID')

    @property
    def is_ready(self):
        """Returns ``True`` if the :class:`.Report` is ready, ``False`` otherwise."""
        if hasattr(self, '_is_ready'):
            return self._is_ready
        report_status = self.session.report_status(self)
        # update attributes
        for s in ['error', 'lines', 'started', 'finished', 'duration']:
            setattr(self, s, report_status[s])
        # don't query status again if report is ready
        if report_status['is_ready']:
            self._is_ready = True
            return True
        return False

    def reload(self, session=None):
        """Reload the `report` status. (alias for :meth:`Report.status`)."""
        self.session = session or self.session
        return self.status

    @property
    def status(self):
        """Reload the :class:`Report` status"""
        if not self.session:
            raise NoSessionError
        if not hasattr(self, 'id'):
            raise ModelNotFoundError("Can't get status without 'id'. "
                                     "Create a report with :meth:`atomx.Atomx.report_get`.")
        status = self.session.report_status(self)
        self.__init__(session=self.session, **status)
        return self

    def get(self, sort=None, limit=None, offset=None):
        """Get the first ``limit`` lines of the report ``content``
        and in the specified ``sort`` order.

        :param str sort: defines the sort order of the report content.
            ``sort`` can be `column_name`[.asc|.desc][,column_name[.asc|.desc]]`...
        :param int limit: limit the amount of lines to return (defaults to no limit)
        :param int offset: Skip the first `offset` number of lines (defaults to none)
        :return: report content
        """
        if not self.is_ready:
            raise ReportNotReadyError()
        return self.session.report_get(self, sort=sort, limit=limit, offset=offset)

    @property
    def content(self):
        """Returns the raw content (csv) of the `report`."""
        if not self.is_ready:
            raise ReportNotReadyError()
        return self.session.report_get(self)

    @property
    def csv(self):
        """Returns the report content (csv) as a list of lists."""
        if not self.is_ready:
            raise ReportNotReadyError()
        return list(csv.reader(self.content.splitlines(), delimiter='\t'))

    @property
    def pandas(self):
        """Returns the content of the `report` as a pandas data frame."""
        try:
            import pandas as pd
        except ImportError:
            raise NoPandasInstalledError('To get the report as a pandas dataframe you '
                                         'have to have pandas installed. '
                                         'Do `pip install pandas` in your command line.')

        return pd.read_csv(StringIO(self.content), sep='\t',
                           names=self.query.get('groups', []) + self.query.get('sums', []))
