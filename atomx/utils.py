import re
from atomx import models


def get_model_name(name):
    """Checks that :param:`name` is a valid model.
    Converts plural `name` to capitalized singular form,
    rstrips '_list' (e.g. `advertisers_list`)
    and '-' or '_' separation to camelCase.
    Returns the name of the model if found, False otherwise.
    E.g.

    >>> check_model_name('countries')
    "Country"
    >>> check_model_name('ADVERTISERS')
    "Advertiser"
    >>> check_model_name('conversion-pixels')
    "ConversionPixel"
    >>> check_model_name('operating_system')
    "OperatingSystem"
    >>> check_model_name('InvalidModel')
    False
    >>> check_model_name('advertisers_list')
    "Advertiser"

    :param str name: model name to convert
    :return: name of the model or False
    """
    if name.endswith('_list'):
        name = name[:-5]
    if '-' in name:
        model_name = ''.join(m.capitalize() for m in name.split('-'))
    elif '_' in name:
        model_name = ''.join(m.capitalize() for m in name.split('_'))
    else:
        model_name = name.capitalize()

    if model_name.endswith('ies'):  # change e.g. Countries to Countr*y*
        model_name = model_name[:-3]+'y'
    else:
        model_name = model_name.rstrip('s')
    if model_name in dir(models):
        return model_name
    return False


def get_attribute_model_name(attribute):
    """Checks if an attribute is a valid model like :func:`get_model_name`
    but also strips '_filter', '_include', '_exclude'

    :param str attribute: attribute name to convert
    :return: name of the model or False
    """
    return get_model_name(re.sub('(_filter|_include|_exclude)$', '', attribute))


def model_name_to_rest(name):
    """Gets a name of a :mod:`atomx.models` and transforms it in the
    resource name for the atomx api.
    E.g.::

        >>> assert model_name_to_rest('ConversionPixels') ==  'conversion-pixels'
        >>> assert model_name_to_rest('OperatingSystem') == 'operating-system'
        >>> assert model_name_to_rest('Advertiser') == 'advertiser'

    :param str name: Name of the model to convert
    :return: :class:`str` with the transformed name.
    """
    r = name[0]
    for i in range(1, len(name)):
        if name[i].isupper():
            r += '-'
        r += name[i]
    return r.lower()


class _class_property(object):
    """Decorator to create @classmethod and @property"""
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)
