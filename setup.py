#!/usr/bin/env python

from setuptools import setup, find_packages
from sys import version_info, exit

deps = []

# Python 3 unsupported
if version_info >= (3,):
    print "Sorry, PyPXE doesn't support Python 3."
    exit(1)

# require argparse on Python <2.7
if version_info[0] == 2 and version_info[1] < 7:
    deps.append('argparse')

setup(name='PyPXE',
      version='1.7.2',
      description='Pure Python2 PXE (DHCP-(Proxy)/TFTP/HTTP/NBD) Server',
      url='https://github.com/psychomario/PyPXE',
      license='MIT',
      packages=find_packages(),
      install_requires=deps,
      entry_points={
          'console_scripts': ['pypxe=pypxe.server:main']
      }
)
