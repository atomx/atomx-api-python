# -*- coding: utf-8 -*-

from datetime import (
    datetime,
    timedelta,
)
import requests
from atomx.version import API_VERSION, VERSION
from atomx import models
from atomx.utils import (
    get_model_name,
    model_name_to_rest,
)
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
    :param bool save_response: If `True` save the last api response meta info
        (without the resource payload) in :attr:`.Atomx.last_response`. (default: `True`)
    :return: :class:`.Atomx` session to interact with the api
    """
    def __init__(self, email, password, api_endpoint=API_ENDPOINT, save_response=True):
        self.auth_tkt = None
        self.user = None
        self.email = email
        self.password = password
        self.api_endpoint = api_endpoint.rstrip('/') + '/'
        self.save_response = save_response
        #: Contains the response of the last api call, if `save_response` was set `True`
        self.last_response = None
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
        self.user = models.User(**r.json()['user'])

    def logout(self):
        """Removes authentication token from session."""
        self.auth_tkt = None
        self.user = None
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
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        search_result = r_json['search']

        if self.save_response:
            del r_json['search']
            self.last_response = r_json

        # convert publisher, creative dicts etc from search result to Atomx.model
        for m in search_result.keys():
            model_name = get_model_name(m)
            if model_name:
                search_result[m] = [getattr(models, model_name)(self, **v)
                                    for v in search_result[m]]
        return search_result

    def report(self, scope=None, groups=None, metrics=None, where=None,
               from_=None, to=None, timezone='UTC', emails=None, fast=True):
        """Create a report.

        See the `reporting atomx wiki <http://wiki.atomx.com/doku.php?id=reporting>`_
        for details about parameters and available groups, metrics.

        :param str scope: either 'advertiser', 'publisher' or 'network' to select the type
            of report. If undefined it tries to determine the `scope` automatically based
            on the `groups` and `metrics` parameters and the access rights of the api user.
        :param list groups: columns to group by.
        :param list metrics: columns to sum on.
        :param list where: is a list of expression lists.
            An expression list is in the form of ``[column, op, value]``:

                - ``column`` can be any of the ``groups`` or ``metrics`` parameter columns.
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
        :param emails: One or multiple email addresses that should get
            notified once the report is finished and ready to download.
        :type emails: str or list
        :param bool fast: if `False` the report will always be run against the low level data.
            This is useful for billing reports for example.
            The default is `True` which means it will always try to use aggregate data
            to speed up the query.
        :return: A :class:`atomx.models.Report` model
        """
        report_json = {'timezone': timezone, 'fast': fast}

        if groups:
            report_json['groups'] = groups
        if metrics:
            report_json['metrics'] = metrics
        elif not groups:
            raise MissingArgumentError('Either `groups` or `metrics` have to be set.')

        if scope is None:
            for i in report_json.get('groups', []) + report_json.get('metrics', []):
                if '_network' in i:
                    scope = 'network'
                    break
            else:
                user = self.user
                if len(user.networks) > 0:
                    pass  # user has network access so could be any report (leave scope as None)
                elif len(user.publishers) > 0 and len(user.advertisers) == 0:
                    scope = 'publishers'
                elif len(user.advertisers) > 0 and len(user.publishers) == 0:
                    scope = 'advertisers'

                if scope is None:
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

        if emails:
            if not isinstance(emails, list):
                emails = [emails]
            report_json['emails'] = emails

        r = self.session.post(self.api_endpoint + 'report', json=report_json)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        report = r_json['report']

        if self.save_response:
            del r_json['report']
            self.last_response = r_json

        return models.Report(self, query=r.json()['query'], **report)

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

        if self.save_response:
            self.last_response = r.json()

        return r.json()['report']

    def report_get(self, report, sort=None, limit=None, offset=None):
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

        params = {}
        if limit:
            params['limit'] = int(limit)
        if offset:
            params['offset'] = int(offset)
        if sort:
            params['sort'] = sort

        r = self.session.get(self.api_endpoint + 'report/' + report_id, params=params)
        if not r.ok:
            raise APIError(r.json()['error'])
        return r.content.decode()

    def get(self, resource, *args, **kwargs):
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
                >>>> # or get the same publisher using the id as parameter
                >>> publisher = atomx.get('publisher', 23)
                >>> assert publisher.id == 23
                >>> assert isinstance(publisher, atomx.models.Publisher)

            Get all profiles for advertiser 42::

                >>> profiles = atomx.get('advertiser/42/profiles')
                >>> assert isinstance(profiles, list)
                >>> assert isinstance(profiles[0], atomx.models.Profile)
                >>> assert profiles[0].advertiser.id == 42

        :param args: All non-keyword arguments will get used to compute the ``resource``.
            This makes it easier if you want to work with a variable resource path.

            .. code-block:: python

                advertiser_id = 42
                attribute = 'profiles'
                profiles = atomx.get('advertiser', advertiser_id, attribute)
                # is equivalent to atomx.get('advertiser/42/profiles')

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
        resource = resource.strip('/')
        for a in args:
            resource += '/' + str(a)
        r = self.session.get(self.api_endpoint + resource, params=kwargs)
        if not r.ok:
            raise APIError(r.json()['error'])

        r_json = r.json()
        model_name = r_json['resource']
        res = r_json[model_name]
        if self.save_response:
            del r_json[model_name]
            self.last_response = r_json
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
        model_name = r_json['resource']
        res = r_json[model_name]
        if self.save_response:
            del r_json[model_name]
            self.last_response = r_json
        model = get_model_name(model_name)
        if model and isinstance(res, list):
            return [getattr(models, model)(self, **m) for m in res]
        return res

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
        model_name = r_json['resource']
        res = r_json[model_name]
        if self.save_response:
            del r_json[model_name]
            self.last_response = r_json
        return res

    def delete(self, resource, *args, **kwargs):
        """Send HTTP DELETE to ``resource``.

        :param resource: Name of the resource to `DELETE`.
        :param args: All non-keyword arguments will be used to compute the final ``resource``.
        :param kwargs: Optional keyword arguments will be passed as query string to the
            delete request.
        :return: message or resource returned by the api.
        """
        resource = resource.strip('/')
        for a in args:
            resource += '/' + str(a)
        r = self.session.delete(self.api_endpoint + resource, params=kwargs)
        r_json = r.json()
        if not r.ok:
            raise APIError(r_json['error'])
        model_name = r_json['resource']
        res = r_json[model_name]
        if self.save_response:
            del r_json[model_name]
            self.last_response = r_json
        return res

    def save(self, model):
        """Alias for :meth:`.models.AtomxModel.save` with `session` argument."""
        return model.save(self)

    def create(self, model):
        """Alias for :meth:`.models.AtomxModel.create` with `session` argument."""
        return model.create(self)
