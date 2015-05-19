#!/usr/bin/env python

from setuptools import setup, find_packages
from sys import version_info

deps = []

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")

setup(name='PyPXE',
      version='1.6',
      description='Pure Python2 PXE (DHCP-(Proxy)/TFTP/HTTP/NBD) Server',
      url='https://github.com/psychomario/PyPXE',
      license='MIT',
      packages=find_packages(),
      install_requires=deps,
      entry_points={
          'console_scripts': ['pypxe=pypxe.server:main']
      }
)
