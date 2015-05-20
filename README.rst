atomx api README
================

Simple interface for the atomx rest api.

Example Usage:
--------------

.. code-block:: python

    from atomx import Atomx

    atomx = Atomx('daniel@atomx.com', 'password')
    creatives = atomx.get('Creatives', limit=10)

    for creative in creatives:
        print('Creative ID: {c.id}, state: {c.state}, '
              'name: {c.name}, title: {c.title}'.format(c=creative))

    creative = creatives[0]
    creative.title = 'shiny new title'
    creative.update()


Installation
------------

To install the python atomx api, simply:

.. code-block:: bash

    $ pip install atomx

