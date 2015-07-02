# -*- coding: utf-8 -*-

from datetime import (
    datetime,
    timedelta,
)
import requests
from atomx.version import API_VERSION, VERSION
from atomx import models
from atomx.utils import get_model_name
from atomx.exceptions import (
    APIError,
    ModelNotFoundError,
    InvalidCredentials,
    MissingArgumentError,
)


__title__ = 'atomx'
__version__ = VERSION
__author__ = 'Spot Media Solutions Sdn. Bhd.'
__copyright__ = 'Copyright 2015 Spot Media Solutions Sdn. Bhd.'

API_ENDPOINT = 'https://api.atomx.com/{}'.format(API_VERSION)


class Atomx(object):
    """Interface for the api on api.atomx.com.

    To learn more about the api visit the
    `atomx wiki <http://wiki.atomx.com/doku.php?id=api>`_

    :param str email: email address of your atomx user
    :param str password:  password of your atomx user
    :param str api_endpoint: url for connections to the api
        (defaults to `https://api.atomx.com/{API_VERSION}`)
    :return: :class:`.Atomx` session to interact with the api
    """
    def __init__(self, email, password, api_endpoint=API_ENDPOINT):
        self.auth_tkt = None
        self.email = email
        self.password = password
        self.api_endpoint = api_endpoint.rstrip('/') + '/'
        self.session = requests.Session()
        self.login()

    def login(self, email=None, password=None):
        """Gets new authentication token for user ``email``.

        This method is automatically called in :meth:`__init__` so
        you rarely have to call this method directly.

        :param str email: Use this email instead of the one provided at
            construction time. (optional)
        :param str password: Use this password instead of the one provided at
            construction time. (optional)
        :return: None
        :raises: :class:`.exceptions.InvalidCredentials` if ``email``/``password`` is wrong
        """
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
        self.auth_tkt = r.json()['auth_tkt']

    def logout(self):
        """Removes authentication token from session."""
        self.auth_tkt = None
        self.session.get(self.api_endpoint + 'logout')

    def search(self, query):
        """Search for ``query``.

        Returns a `dict` with all found results for:
        'Advertisers', 'Campaigns', 'Creatives', 'Placements', 'Publishers', 'Sites'.

        The resulting :mod:`.models` have only `id` and `name` loaded since that's
        what's returned from the api `/search` call, but attributes will be lazy loaded
        once you try to accessed them.
        Or you can just fetch everything with one api call with :meth:`.AtomxModel.reload`.

        Example::

            >>> atomx = Atomx('apiuser@example.com', 'password')
            >>> search_result = atomx.search('atomx')
            >>> assert 'campaigns' in search_result
            >>> campaign = search_result['campaigns'][0]
            >>> assert isinstance(campaign, models.Campaign)
            >>> # campaign has only `id` and `name` loaded but you
            >>> # can still access (lazy load) all attributes
            >>> assert isinstance(campaign.budget, float)
            >>> # or reload all attributes with one api call
            >>> campaign.reload()

        :param str query: keyword to search for.
        :return: dict with list of :mod:`.models` as values
        """
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

    def report(self, scope=None, groups=None, sums=None, where=None,
               from_=None, to=None, timezone='UTC', fast=True):
        """Create a report.

        See the `reporting atomx wiki <http://wiki.atomx.com/doku.php?id=reporting>`_
        for details about parameters and available groups, sums.

        :param str scope: either 'advertiser' or 'publisher' to select the type of report.
            If undefined but the groups column have an unambiguous attribute that's
            unique to a certain scope, it's set automatically.
        :param list groups: columns to group by.
        :param list sums: columns to sum on.
        :param list where: is a list of expression lists.
            An expression list is in the form of ``[column, op, value]``:

                - ``column`` can be any of the ``groups`` or ``sums`` parameter columns.
                - ``op`` can be any of ``==``, ``!=``, ``<=``, ``>=``,
                  ``<``, ``>``, ``in`` or ``not in`` as a string.
                - ``value`` is either a number or in case of ``in``
                  and ``not in`` a list of numbers.

        :param datetime.datetime from_: :class:`datetime.datetime` where the report
            should start (inclusive). (defaults to last week)
        :param datetime.datetime to: :class:`datetime.datetime` where the report
            should end (exclusive). (defaults to `datetime.now()` if undefined)
        :param str timezone:  Timezone used for all times. (defaults to `UTC`)
            For a supported list see http://wiki.atomx.com/doku.php?id=timezones
        :param bool fast: if `False` the report will always be run against the low level data.
            This is useful for billing reports for example.
            The default is `True` which means it will always try to use aggregate data
            to speed up the query.
        :return: A :class:`atomx.models.Report` model
        """
        report_json = {'timezone': timezone, 'fast': fast}

        if groups:
            report_json['groups'] = groups
        if sums:
            report_json['sums'] = sums
        elif not groups:
            raise MissingArgumentError('Either `groups` or `sums` have to be set.')

        if scope is None:
            for i in report_json.get('groups', []) + report_json.get('sums', []):
                if i.split('_')[0] in ['advertiser', 'campaign', 'creative', 'pixel']:
                    scope = 'advertiser'
                    break
            else:
                for i in report_json.get('groups', []) + report_json.get('sums', []):
                    if i.split('_')[0] in ['site', 'placement', 'user']:
                        scope = 'publisher'
                        break
                else:
                    raise MissingArgumentError('Unable to detect scope automatically. '
                                               'Please set `scope` parameter.')
        report_json['scope'] = scope

        if where:
            report_json['where'] = where

        if from_ is None:
            from_ = datetime.now() - timedelta(days=7)
        if isinstance(from_, datetime):
            report_json['from'] = from_.strftime("%Y-%m-%d %H:00:00")
        else:
            report_json['from'] = from_

        if to is None:
            to = datetime.now()
        if isinstance(to, datetime):
            report_json['to'] = to.strftime("%Y-%m-%d %H:00:00")
        else:
            report_json['to'] = to

        r = self.session.post(self.api_endpoint + 'report', json=report_json)
        if not r.ok:
            raise APIError(r.json()['error'])
        return models.Report(self, query=r.json()['query'], **r.json()['report'])

    def report_status(self, report):
        """Get the status for a `report`.

        This is typically used by calling :meth:`.models.Report.status`.

        :param report: Either a :class:`str` that contains the ``id`` of
            of the report or an :class:`.models.Report` instance.
        :type report: :class:`.models.Report` or :class:`list`
        :return: :class:`dict` containing the report status.
        """
        if isinstance(report, models.Report):
            report_id = report.id
        else:
            report_id = report

        r = self.session.get(self.api_endpoint + 'report/' + report_id, params={'status': True})
        if not r.ok:
            raise APIError(r.json()['error'])
        return r.json()['report']

    def report_get(self, report):
        """Get the content (csv) of a :class:`.models.Report`

        Typically used by calling :meth:`.models.Report.content` or
        :meth:`.models.Report.pandas`.

        :param report: Either a :class:`str` that contains the ``id`` of
            of the report or an :class:`.models.Report` instance.
        :type report: :class:`.models.Report` or :class:`list`
        :return: :class:`str` with the report content.
        """
        if isinstance(report, models.Report):
            report_id = report.id
        else:
            report_id = report

        r = self.session.get(self.api_endpoint + 'report/' + report_id)
        if not r.ok:
            raise APIError(r.json()['error'])
        return r.content.decode()

    def get(self, resource, **kwargs):
        """Returns a list of models from :mod:`.models` if you query for
        multiple models or a single instance of a model from :mod:`.models`
        if you query for a specific `id`

        :param str resource: Specify the resource to get from the atomx api.

            Examples:

            Query all advertisers::

                >>> atomx = Atomx('apiuser@example.com', 'password')
                >>> advertisers = atomx.get('advertisers')
                >>> assert isinstance(advertisers, list)
                >>> assert isinstance(advertisers[0], atomx.models.Advertiser)

            Get publisher with id 23::

                >>> publisher = atomx.get('publisher/23')
                >>> assert publisher.id == 23
                >>> assert isinstance(publisher, atomx.models.Publisher)

            Get all profiles for advertiser 42::

                >>> profiles = atomx.get('advertiser/42/profiles')
                >>> assert isinstance(profiles, list)
                >>> assert isinstance(profiles[0], atomx.models.Profile)
                >>> assert profiles[0].advertiser.id == 42

        :param kwargs: Any argument is passed as URL parameter to the respective api endpoint.
            See `API URL Parameters <http://wiki.atomx.com/doku.php?id=api#url_parameters>`_
            in the wiki.

            Example:
            Get the first 20 domains that contain ``atom``::

                >>> atom_domains = atomx.get('domains', hostname='*atom*', limit=20)
                >>> assert len(atom_domains) == 20
                >>> assert 'atom' in atom_domains[1].hostname

        :return: a class from :mod:`.models` or a list of models depending on param `resource`
        """
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

    def post(self, resource, json, **kwargs):
        """Send HTTP POST to ``resource`` with ``json`` content.

        Used by :meth:`.models.AtomxModel.create`.

        :param resource: Name of the resource to `POST` to.
        :param json: Content of the `POST` request.
        :param kwargs: URL Parameters of the request.
        :return: :class:`dict` with the newly created resource.
        """
        r = self.session.post(self.api_endpoint + resource.strip('/'),
                              json=json, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        return r_json[r_json['resource']]

    def put(self, resource, id, json, **kwargs):
        """Send HTTP PUT to ``resource``/``id`` with ``json`` content.

        Used by :meth:`.models.AtomxModel.save`.

        :param resource: Name of the resource to `PUT` to.
        :param id: Id of the resource you want to modify
        :param json: Content of the `PUT` request.
        :param kwargs: URL Parameters of the request.
        :return: :class:`dict` with the modified resource.
        """
        r = self.session.put(self.api_endpoint + resource.strip('/') + '/' + str(id),
                             json=json, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        return r_json[r_json['resource']]

    def delete(self, resource, id, json, **kwargs):
        """Delete is currently not supported by the api.
        Set the resources `state` to `INACTIVE` to deactivate it.
        """
        pass

    def save(self, model):
        """Alias for :meth:`.models.AtomxModel.save` with `session` argument."""
        return model.save(self)

    def create(self, model):
        """Alias for :meth:`.models.AtomxModel.create` with `session` argument."""
        return model.create(self)
