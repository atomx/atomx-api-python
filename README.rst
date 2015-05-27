atomx api README
================

Simple interface for the atomx rest api.

Example Usage:
--------------

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
    creative.update()


    # create a new profile
    from atomx.models import Profile
    profile = Profile(advertiser_id=23, name='test profile')
    # Note that you have to pass it a valid `Atomx` session for save
    # or use `atomx.save(profile)`
    profile.save(atomx)

    # now you could alter and update it like the creative above
    profile.name = 'changed name'
    profile.update()


    # you can also get attributes
    profiles = atomx.get('advertiser/88/profiles')
    # profiles is now a list of `atomx.models.Profile` that you can
    # read, update, etc again.
    profiles[0].click_frequency_cap_per = 86400
    profiles[0].update()


    # working with search
    s = atomx.search('mini*')
    # s is now a dict with lists of search results for the different models
    # with the model id and name

    publisher = s['publisher'][0]  # get the first publisher..
    publisher.reload()  # .. and load all the data
    print(publisher)  # now all publisher data is there


    # reporting example
    # get a report for a specific publisher
    report = atomx.report(type='publisher', sums=['impressions', 'clicks'], groups=['hour'], where=[['publisher_id', '==', 42]], from_='2015-02-08 00:00:00Z', to='2015-02-09 00:00:00Z')
    # check if report is ready
    print(report.is_ready)
    # if pandas is installed you can get the pandas dataframe with `report.pandas`
    # you can also get the report csv in `report.content` without pandas
    df = report.pandas
    # set index to datetime
    import pandas as pd
    df.index = pd.to_datetime(df.pop('hour'))
    # resample per day
    means = df.resample('D', how=['mean', 'median', 'std'])
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
