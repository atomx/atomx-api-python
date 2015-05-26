# -*- coding: utf-8 -*-

import pprint
from .exceptions import NoSessionError, ModelNotFoundError, APIError

__all__ = ['Advertiser', 'Bidder', 'Browser', 'Campaign', 'Category', 'ConnectionType',
           'ConversionPixel', 'Country', 'Creative', 'Datacenter', 'DeviceType',
           'Domain', 'Fallback', 'Isp', 'Languages', 'Network', 'OperatingSystem',
           'Placement', 'Profile', 'Publisher', 'Reason', 'Segment', 'Seller',
           'Site', 'Size', 'User']


class AtomxModel(object):
    def __init__(self, session=None, **attributes):
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

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, pprint.pformat(self.json))

    @property
    def _dirty_json(self):
        return {k: self._attributes[k] for k in self._dirty}

    @property
    def json(self):
        return self._attributes

    def create(self, session=None):
        session = session or self.session
        if not session:
            raise NoSessionError
        res = session.post(self.__class__.__name__, json=self.json)
        self.__init__(session=session, **res)
        return self

    def update(self, session=None):
        return self.save(session)

    def save(self, session=None):
        session = session or self.session
        if not session:
            raise NoSessionError
        res = session.put(self.__class__.__name__, self.id, json=self._dirty_json)
        self.__init__(session=session, **res)
        return self

    def delete(self, session=None):
        session = session or self.session
        if not session:
            raise NoSessionError
        return session.delete(self.__class__.__name__, self.id, json=self._dirty_json)

    def reload(self, session=None):
        session = session or self.session
        if not session:
            raise NoSessionError
        if not hasattr(self, 'id'):
            raise ModelNotFoundError("Can't reload without 'id' parameter. "
                                     "Forgot to save() first?")
        res = session.get(self.__class__.__name__ + '/' + str(self.id))
        self.__init__(session=session, **res.json)
        return self


for m in __all__:
    locals()[m] = type(m, (AtomxModel,), {})
