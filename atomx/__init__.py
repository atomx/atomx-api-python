# -*- coding: utf-8 -*-

from datetime import datetime
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

API_ENDPOINT = 'https://api.atomx.com/{}'.format(API_VERSION)


class Atomx(object):
    def __init__(self, email, password, api_endpoint=API_ENDPOINT):
        self.email = email
        self.password = password
        self.api_endpoint = api_endpoint.rstrip('/') + '/'
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
        search_result = r.json()['search']
        # convert publisher, creative dicts etc from search result to Atomx.model
        for m in search_result.keys():
            model_name = get_model_name(m)
            if model_name:
                search_result[m] = [getattr(models, model_name)(self, **v)
                                    for v in search_result[m]]
        return search_result

    def report(self, scope, groups, sums, where, from_, to=None, timezone='UTC', fast=True):
        """Create a report.

        :param str scope: either 'advertiser' or 'publisher' to select the type of report.
        :param list groups: columns to group by (see http://wiki.atomx.com/doku.php?id=reporting#groups)
        :param list sums: columns to sum on (see http://wiki.atomx.com/doku.php?id=reporting#sums)
        :param list where: is a list of expression lists.
            An expression list is in the form of `[column, op, value]`.
            `column` can be any of the :param:`groups` or :param:`sums` columns.
            `op` can be any of `==`, `!=`, `<=`, `>=`, `<`, `>`, `in` or `not in` as a string.
            `value` is either a number or in case of `in` and `not in` a list of numbers.
        :param datetime from_: `datetime` where the report should start (inclusive)
        :param datetime to: `datetime` where the report should end (exclusive).
            (defaults to `datetime.now()` if undefined)
        :param str timezone:  Timezone used for all times. (defaults to `UTC`)
            For a supported list see http://wiki.atomx.com/doku.php?id=timezones
        :param bool fast: if `False` the report will always be run against the low level data.
            This is useful for billing reports for example.
            The default is `True` which means it will always try to use aggregate data
            to speed up the query.
        :return: A :class:`atomx.models.Report` model
        """
        report_json = locals().copy()
        del report_json['self']

        if to is None:
            report_json['to'] = datetime.now()
        if isinstance(report_json['to'], datetime):
            report_json['to'] = report_json['to'].strftime("%Y-%m-%d %H:00:00")
        if isinstance(report_json.get('from_'), datetime):
            report_json['from'] = report_json['from_'].strftime("%Y-%m-%d %H:00:00")
        else:
            report_json['from'] = report_json['from_']
        del report_json['from_']
        r = self.session.post(self.api_endpoint + 'report', json=report_json)
        if not r.ok:
            raise APIError(r.json()['error'])
        return models.Report(self, query=r.json()['query'], **r.json()['report'])

    def report_status(self, report):
        if isinstance(report, models.Report):
            report_id = report.id
        else:
            report_id = report

        r = self.session.get(self.api_endpoint + 'report/' + report_id, params={'status': True})
        if not r.ok:
            raise APIError(r.json()['error'])
        return r.json()['report']

    def report_get(self, report):
        if isinstance(report, models.Report):
            report_id = report.id
        else:
            report_id = report

        r = self.session.get(self.api_endpoint + 'report/' + report_id)
        if not r.ok:
            raise APIError(r.json()['error'])
        return r.content.decode()

    def get(self, resource, **kwargs):
        r = self.session.get(self.api_endpoint + resource.strip('/'), params=kwargs)
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
        r = self.session.post(self.api_endpoint + model.strip('/'),
                              json=json, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        return r_json[r_json['resource']]

    def put(self, model, id, json, **kwargs):
        r = self.session.put(self.api_endpoint + model.strip('/') + '/' + str(id),
                             json=json, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        return r_json[r_json['resource']]

    def delete(self, model, id, json, **kwargs):
        return self.session.put(self.api_endpoint + model.strip('/') + '/' + str(id),
                                json=json, params=kwargs)

    def save(self, model):
        return model.save(self)

    def update(self, model):
        return model.update(self)
