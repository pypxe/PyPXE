#!/usr/bin/env python

from setuptools import setup, find_packages
from sys import version_info, exit

import pypxe

deps = []

setup(name='PyPXE',
      version=pypxe.__version__,
      description='Pure Python PXE (DHCP-(Proxy)/TFTP/HTTP/NBD) Server',
      url='https://github.com/pypxe/PyPXE',
      license='MIT',
      packages=find_packages(),
      install_requires=deps,
      entry_points={
          'console_scripts': ['pypxe=pypxe.server:main']
      }
)
