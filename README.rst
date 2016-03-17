Python Atomx Api
================

Interface for the atomx rest api.

For more information read the full
`documentation online <http://atomx-api-python.readthedocs.org/en/latest/index.html>`_,
report bugs in `github <https://github.com/atomx/atomx-api-python>`_
or see the `atomx wiki <https://wiki.atomx.com/api>`_


Example Usage
-------------

.. code-block:: python

    from atomx import Atomx

    # create atomx session
    atomx = Atomx('user@example.com', 'password')

    # get 10 creatives
    creatives = atomx.get('Creatives', limit=10)
    # the result is a list of `atomx.models.Creative` models
    # that you can easily inspect, manipulate and update
    for creative in creatives:
        print('Creative ID: {c.id}, state: {c.state}, '
              'name: {c.name}, title: {c.title}'.format(c=creative))

    # update title for the first creative in list
    creative = creatives[0]
    creative.title = 'shiny new title'
    # the session is inherited from `atomx` that made the get request
    creative.save()


    # create a new profile
    from atomx.models import Profile
    profile = Profile(advertiser_id=23, name='test profile')
    # Note that you have to pass it a valid `Atomx` session for create
    # or use `atomx.create(profile)`
    profile.create(atomx)

    # now you could alter and update it like the creative above
    profile.name = 'changed name'
    profile.save()


    # you can also get attributes
    profiles = atomx.get('advertiser', 88, 'profiles')
    # equivalent is to pass the complete resource path as string instead of arguments
    profiles = atomx.get('advertiser/88/profiles')  # same as above
    # profiles is now a list of `atomx.models.Profile` that you can
    # read, update, etc again.
    profiles[0].click_frequency_cap_per = 86400
    profiles[0].save()


    # working with search
    s = atomx.search('mini*')
    # s is now a dict with lists of search results for the different models
    # with the model id and name

    publisher = s['publisher'][0]  # get the first publisher..
    publisher.reload()  # .. and load all the data
    print(publisher)  # now all publisher data is there
    publisher.history()  # gets all changes made to this publisher


    # reporting example
    # get a report for a specific publisher
    report = atomx.report(scope='publisher', groups=['hour'], metrics=['impressions', 'clicks'], where=[['publisher_id', '==', 42]], from_='2015-02-08 00:00:00', to='2015-02-09 00:00:00', timezone='America/Los_Angeles')
    # check if report is ready
    print(report.is_ready)
    # if pandas is installed you can get the pandas dataframe with `report.pandas`
    # you can also get the report csv in `report.content` without pandas
    df = report.pandas  # A datetime index is automatically set when group by a hour/day/month.
    # calculate mean, median, std per hour
    means = df.resample('H', how=['mean', 'median', 'std'])
    # and plot impression and clicks per day
    means['impressions'].plot()
    means['clicks'].plot()


Installation
------------

To install the python atomx api, simply:

.. code-block:: bash

    $ pip install atomx

or if you want to use ipython notebook and reporting functionality:

.. code-block:: bash

    $ pip install atomx[report]
