from setuptools import find_packages, setup

setup(name="Data Servants: Tools for Wrangling Astronomical Data",
      version="0.5",
      description="Modules for handling data spread across a variety of data-generating host machines",
      author="Ryan T. Hamilton",
      author_email='rhamilton@lowell.edu',
      platforms=["any"],  # or more specific, e.g. "win32", "cygwin", "osx"
      license="MPL 2.0",
      url="https://github.com/astrobokonon/DataServants",
      packages=find_packages(),
      )
