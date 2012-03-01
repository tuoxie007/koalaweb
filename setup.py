from distutils.core import setup
from koalaweb import __version__

setup(name="koalaweb",
      version=__version__,
      author=__author__
      author_email=__email__
      description="Web Framework for lazy man like koala",
      long_description="""Itelligent route, easy context access, powerful template engine.
Appoint is greater than configuration""",
      py_modules=['koalaweb'],
      license="BSD",
      url="http://tuoxie.me/blog/koalaweb",
      download_url="https://github.com/tuoxie007/koalaweb",
     )
