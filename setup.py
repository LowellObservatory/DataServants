from setuptools import find_packages, setup

setup(name="Wadsworth: The Data Butler",
      version="0.5",
      description="Modules for handling data on a variety of hosts",
      author="Ryan T. Hamilton",
      author_email='rhamilton@lowell.edu',
      platforms=["any"],  # or more specific, e.g. "win32", "cygwin", "osx"
      license="MPL 2.0",
      url="https://github.com/astrobokonon/Wadsworth",
      packages=find_packages(),
      )
