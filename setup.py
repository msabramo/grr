#!/usr/bin/env python3
from setuptools import setup

setup(
    name='grr',
    version='0.1',
    author='Kunal Mehta',
    author_email='legoktm@gmail.com',
    url='https://github.com/legoktm/grr/',
    license='CC-0',
    description='A command-line utility to work with Gerrit',
    long_description=open('README.rst').read(),
    packages=['grr'],
    entry_points={
        'console_scripts': [
            'grr = grr:main'
        ],
    }
)