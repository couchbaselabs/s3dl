from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='s3dl',
      version=version,
      description="Makes downloading s3 files easier",
      long_description="",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Will Gardner',
      author_email='will.gardner@couchbase.com',
      url='',
      license='MIT',
      packages=['s3dl'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'boto3'
      ],
      entry_points={
        "console_scripts": [
            "s3dl=s3dl.__main__:main",
        ],
      })
