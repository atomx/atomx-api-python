# -*- coding: utf-8 -*-

import requests
from .version import API_VERSION, VERSION
from . import models
from .utils import get_model_name
from .exceptions import (
    APIError,
    ModelNotFoundError,
    InvalidCredentials,
)


__title__ = 'atomx'
__version__ = VERSION
__author__ = 'Spot Media Solutions Sdn. Bhd.'
__copyright__ = 'Copyright 2015 Spot Media Solutions Sdn. Bhd.'

API_ENDPOINT = 'http://api.atomx.com/{}/'.format(API_VERSION)


class Atomx(object):
    def __init__(self, email, password, api_endpoint=API_ENDPOINT):
        self.email = email
        self.password = password
        self.api_endpoint = api_endpoint
        self.session = requests.Session()
        self.login()

    def login(self, email=None, password=None):
        if email:
            self.email = email
        if password:
            self.password = password

        r = self.session.post(self.api_endpoint + 'login',
                              json={'email': self.email, 'password': self.password})
        if not r.ok:
            if r.status_code == 401:
                raise InvalidCredentials
            raise APIError(r.json()['error'])
        self.auth_tk = r.json()['auth_tkt']

    def logout(self):
        self.session.get(self.api_endpoint + 'logout')

    def search(self, query):
        r = self.session.get(self.api_endpoint + 'search', params={'q': query})
        if not r.ok:
            raise APIError(r.json()['error'])
        return r.json()['search']

    def get(self, resource, **kwargs):
        r = self.session.get(self.api_endpoint + resource, params=kwargs)
        if not r.ok:
            raise APIError(r.json()['error'])

        r_json = r.json()
        model_name = r_json['resource']
        res = r_json[model_name]
        model = get_model_name(model_name)
        if model:
            if isinstance(res, list):
                return [getattr(models, model)(self, **m) for m in res]
            return getattr(models, model)(self, **res)
        return res

    def post(self, model, json, **kwargs):
        r = self.session.post(self.api_endpoint + model, json=json, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        return r_json[r_json['resource']]

    def put(self, model, id, json, **kwargs):
        r = self.session.put(self.api_endpoint + model + '/' + str(id), json=json, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        return r_json[r_json['resource']]

    def delete(self, model, id, json, **kwargs):
        return self.session.put(self.api_endpoint + model + '/' + str(id), json=json, params=kwargs)

    def save(self, model):
        return model.save(self)

    def update(self, model):
        return model.update(self)
