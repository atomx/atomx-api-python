from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    README = f.read()
with open(path.join(here, 'atomx', 'version.py')) as f:
    exec(f.read())  # defines VERSION and API_VERSION


requires = [
    'requests',
]
extra_require = {
    'report': ['ipython[notebook]', 'pandas', 'matplotlib'],
    'test': ['pytest'],
    'docs': ['sphinx'],
}

setup(
    name='atomx',
    version=VERSION,

    description='python interface for the atomx api on https://api.atomx.com',
    long_description=README,

    packages=find_packages(),
    exclude_package_data={'': ['.gitignore']},
    zip_safe=True,

    author='Spot Media Solutions Sdn. Bhd.',
    author_email='daniel@atomx.com',
    url='https://github.com/atomx/atomx-api-python',
    license='ISC',
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

    setup_requires=['setuptools_git'],
    tests_require=['pytest'],
    install_requires=requires,
    extras_require=extra_require,
)
