# -*- coding: utf-8 -*-

import csv
import pprint
from decimal import Decimal
from datetime import datetime, date
try:  # py3
    from io import StringIO
except ImportError:  # py2
    from StringIO import StringIO
from atomx.exceptions import (
    NoSessionError,
    ModelNotFoundError,
    APIError,
    ReportNotReadyError,
    NoPandasInstalledError,
)

__all__ = ['Advertiser', 'Bidder', 'Browser', 'Campaign', 'Category', 'ConnectionType',
           'ConversionPixel', 'Country', 'Creative', 'Datacenter', 'DeviceType',
           'Domain', 'Fallback', 'Isp', 'Languages', 'Network', 'OperatingSystem',
           'Placement', 'Profile', 'Publisher', 'Reason', 'Segment', 'SellerProfile',
           'Site', 'Size', 'User']


class AtomxModel(object):
    """A generic atomx model that the other models from :mod:`atomx.models` inherit from.

    :param atomx.Atomx session: The :class:`atomx.Atomx` session to use for the api requests.
    :param attributes: model attributes
    """
    def __init__(self, session=None, **attributes):
        """Atomx model for {model}. test
        :param session: session
        :param attributes: attributes
        :return: model.{model}
        """
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
                v = self.session.get(self.__class__.__name__ + '/' +
                                     str(self.id) + '/' + str(item))
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
        else:
            self._attributes[item] = None
            self._dirty.add(item)

    def __dir__(self):
        """Manually add dynamic attributes for autocomplete"""
        return dir(type(self)) + list(self.__dict__.keys()) + list(self._attributes.keys())

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, pprint.pformat(self.json))

    def __eq__(self, other):
        return self.id == getattr(other, 'id', 'INVALID')

    @property
    def _resource_name(self):
        from atomx.utils import model_name_to_rest
        return model_name_to_rest(self.__class__.__name__)

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


for m in __all__:
    locals()[m] = type(m, (AtomxModel,),
                       {'__doc__': ':class:`.AtomxModel` for {}'.format(m)})


class Report(object):
    """Represents a `report` you get back from :meth:`atomx.Atomx.report`."""

    def __init__(self, session, query, fast, id, lines, error, link,
                 started, finished, is_ready, duration, **kwargs):
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

        if is_ready:
            self._is_ready = is_ready

    def __repr__(self):
        return "Report(id='{}', is_ready={}, query={})".format(self.id, self.is_ready, self.query)

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
