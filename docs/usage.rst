Usage
=====

Creating a session
------------------

To work with the api you need to get a user from
`atomx <https://www.atomx.com>`_ and create a
:class:`atomx.Atomx` session using your email and password:

.. code-block:: python

    from atomx import Atomx

    # create atomx session
    atomx = Atomx('user@example.com', 'password')

optionally you can specify a different api endpoint for testing:

.. code-block:: python

    # create atomx session with sandbox endpoint
    atomx = Atomx('user@example.com', 'password',
                  api_endpoint='https://sandbox.api.atomx.com/v1')


Fetching resources
------------------

Use :meth:`atomx.Atomx.get` to fetch any resource from the api.
The first parameter is the resource you want to query and can be any
string that the `atomx api <http://wiki.atomx.com/doku.php?id=api>`_ accepts.
All additional keyword arguments are used to build the query string.

If the returned resource (or list of resources) is any of the
:mod:`atomx.models` then that model instance will be returned so
you can easily work with it.


For example to get 10 creatives and then print some information about it:

.. code-block:: python

    # get 10 creatives
    creatives = atomx.get('Creatives', limit=10)
    # the result is a list of `atomx.models.Creative` models
    # that you can easily inspect, manipulate and update
    for creative in creatives:
        print('Creative ID: {c.id}, state: {c.state}, '
              'name: {c.name}, title: {c.title}'.format(c=creative))

Or query all profiles of advertiser 42 ordered by last updated:

.. code-block:: python

    profiles = atomx.get('advertiser/42/profiles', order_by='updated_at.desc')


Or get all domains where the hostname contains `atom`:

.. code-block:: python

    domains = atomx.get('domains', name='*atom*')


Attributes that are not loaded in the model will be lazy loaded once you
try to access them.
E.g. if you want to access the `quickstats` for the creative
we fetched earlier you don't have to to anything special,
just access the `quickstats` attribute:

.. code-block:: python

    creative = creatives[0]
    print(creative.quickstats)

Or to get the advertiser for a profile, just:

.. code-block:: python

    advertiser = profiles[0].advertiser


Updating models
---------------

To change a :mod:`atomx.models` model you just change
any attribute you want and call :meth:`atomx.models.AtomxModel.save`.

E.g.

.. code-block:: python

    # update title for the first creative in list
    creative = creatives[0]
    creative.title = 'shiny new title'
    creative.save()

    # update profile click frequency
    profiles[0].click_frequency_cap_per = 86400
    profiles[0].save()



Creating models
---------------

To add a new entry in `atomx` just instantiate any :mod:`atomx.models`
model with all attributes you want your newly created model to have
and either call :meth:`atomx.models.AtomxModel.create` with your
:class:`atomx.Atomx` session as parameter or use
:meth:`atomx.Atomx.save`.

E.g. create a new profile entry:

.. code-block:: python

    # create a new profile
    from atomx.models import Profile
    profile = Profile(advertiser_id=23, name='test profile')
    # Note that you have to pass it a valid `Atomx` session for create
    # or use `atomx.create(profile)`
    profile.create(atomx)


Search
------

Use :meth:`atomx.Atomx.search` to search fast for anything.

:meth:`atomx.Atomx.search` returns a `dict` with all found results for:
'Advertisers', 'Campaigns', 'Creatives', 'Placements', 'Publishers', 'Sites'.

The resulting :mod:`.models` have only `id` and `name` loaded since that's
what's returned from the api `/search` call, but attributes will be lazy loaded
once you try to accessed them.
Or you can just fetch everything with one api call with :meth:`.AtomxModel.reload`.

Example:

.. code-block:: python

    search_result = atomx.search('atomx')

    campaign = search_result['campaigns'][0]
    assert isinstance(campaign, models.Campaign)

    # campaign has only `id` and `name` loaded but you
    # can still access (lazy load) all attributes
    print(campaign.budget)
    print(campaign.profile)

    # or reload all attributes with one api call
    campaign.reload()


Reports
-------

See :meth:`atomx.Atomx.report` for a description of available parameters
to create a report.

.. code-block:: python

    # reporting example
    # get a report for a specific publisher
    report = atomx.report(scope='publisher', groups=['hour_formatted'], sums=['impressions', 'clicks'], where=[['publisher_id', '==', 42]], from_='2015-02-08 00:00:00', to='2015-02-09 00:00:00', timezone='America/Los_Angeles')
    # check if report is ready
    print(report.is_ready)
    # if pandas is installed you can get the pandas dataframe with `report.pandas`
    # you can also get the report csv in `report.content` without pandas
    df = report.pandas
    # set index to datetime
    import pandas as pd
    df.index = pd.to_datetime(df.pop('hour_formatted'))
    # calculate mean, median, std per hour
    means = df.resample('H', how=['mean', 'median', 'std'])
    # and plot impression and clicks per day
    means['impressions'].plot()
    means['clicks'].plot()

For more general information about atomx reporting visit the
`reporting atomx knowledge base entry <https://wiki.atomx.com/doku.php?id=reporting>`_.