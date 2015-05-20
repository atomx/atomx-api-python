# -*- coding: utf-8 -*-

from .exceptions import NoSessionError


__all__ = ['Advertiser', 'Campaign', 'Creative', 'Fallback', 'Network', 'Placement', 'Profile',
           'Publisher', 'Segment', 'Site', 'User']


class AtomxModel(object):
    def __init__(self, session=None, **attributes):
        super(AtomxModel, self).__setattr__('session', session)
        super(AtomxModel, self).__setattr__('_attributes', attributes)
        super(AtomxModel, self).__setattr__('_dirty', set())  # list of changed attributes

    def __getattr__(self, item):
        return self._attributes.get(item)

    def __setattr__(self, key, value):
        if self._attributes[key] != value:
            self._attributes[key] = value
            self._dirty.add(key)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._attributes)

    @property
    def _dirty_json(self):
        return {k: self._attributes[k] for k in self._dirty}

    @property
    def json(self):
        return self._attributes

    def save(self, session=None):
        session = session or self.session
        if not session:
            raise NoSessionError
        res = session.post(self.__class__.__name__, json=self.json)
        self.__init__(session=session, **res)
        return self

    def update(self, session=None):
        session = session or self.session
        if not session:
            raise NoSessionError
        res = self.session.put(self.__class__.__name__, self.id, json=self._dirty_json)
        self.__init__(session=session, **res)
        return self

    def delete(self, session=None):
        if not session and not self.session:
            raise NoSessionError
        return self.session.delete(self.__class__.__name__, self.id, json=self._dirty_json)


for m in __all__:
    locals()[m] = type(m, (AtomxModel,), {})
