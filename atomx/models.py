# -*- coding: utf-8 -*-

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
    NoPandasInstalledError,
)

__all__ = ['AccountManager', 'Advertiser', 'Bidder', 'Browser',
           'CampaignDebugReason', 'Campaign', 'Category', 'ConnectionType',
           'ConversionPixel', 'Country', 'Creative', 'CreativeAttribute',
           'Datacenter', 'DeviceType', 'Domain', 'Fallback', 'Isp', 'Languages', 'Network',
           'OperatingSystem', 'Placement', 'PlacementType', 'Profile', 'Publisher', 'Reason',
           'Segment', 'SellerProfile', 'Site', 'Size', 'User', 'Visibility',
           'Report']


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
        from atomx.utils import get_attribute_model_name
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


class Report(object):
    """Represents a `report` you get back from :meth:`atomx.Atomx.report`."""

    def __init__(self, id, query=None, name=None, emails=None, length=None, totals=None,
                 columns=None, created_at=None, data=None, user_id=None, session=None,
                 is_scheduled_report=False, **kwargs):
        self.session = session
        self.id = id
        self.user_id = user_id
        self.name = name
        self.emails = emails
        self.query = query
        self.data = data
        self.length = length
        self.totals = totals
        self.columns = columns
        self.created_at = created_at
        self.is_scheduled_report = is_scheduled_report

    def __repr__(self):
        return "Report(created_at={}, query={})".format(self.created_at, self.query)

    def __eq__(self, other):
        return self.id == getattr(other, 'id', 'INVALID')

    @_class_property
    def _resource_name(cls):
        return 'report'

    def save(self, session=None):
        """Update report `name` and `emails`"""

        session = session or self.session
        if not session:
            raise NoSessionError
        return session.put('report', self.id, {'name': self.name, 'emails': self.emails})

    def delete(self, session=None):
        """Delete report"""

        session = session or self.session
        if not session:
            raise NoSessionError
        return session.delete('report', self.id)

    @property
    def pandas(self):
        """Returns the content of the `report` as a pandas data frame."""
        if hasattr(self, '_pandas_df'):
            return self._pandas_df

        try:
            import pandas as pd
        except ImportError:
            raise NoPandasInstalledError('To get the report as a pandas dataframe you '
                                         'have to have pandas installed. '
                                         'Do `pip install pandas` in your command line.')

        res = pd.DataFrame(self.data, columns=self.columns)
        groups = self.query.get('groups', [])
        if 'hour' in groups:
            res.index = pd.to_datetime(res.pop('hour'))
        elif 'day' in groups:
            res.index = pd.to_datetime(res.pop('day'))
        elif 'month' in groups:
            res.index = pd.to_datetime(res.pop('month'))

        self._pandas_df = res
        return res
