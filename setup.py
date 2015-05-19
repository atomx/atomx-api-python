from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst')) as f:
    README = f.read()
with open(path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()
with open(path.join(here, 'atomx', 'version.py')) as f:
    exec(f.read())  # defines VERSION and API_VERSION

from distutils.core import setup

requires = [
    'requests',
]

setup(
    name='atomx',
    version=VERSION,

    description='python interface for the https://api.atomx.com',
    long_description=README + '\n\n' + CHANGES,

    packages=find_packages(),
    zip_safe=True,
    url='https://github.com/atomx/atomx-api-python',
    license='ISC',
    author='Spot Media Solutions Sdn. Bhd.',
    author_email='daniel@atomx.com',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='atomx rest api',

    install_requires=requires,
    extra_require={
        'test': 'pytest',
        'docs': 'sphinx',
    }
)
