# This file is part of Checkbox.
#
# Copyright 2012 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# Checkbox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Checkbox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Checkbox.  If not, see <http://www.gnu.org/licenses/>.

"""
:mod:`plainbox.tests` -- auxiliary test loaders for plainbox
============================================================
"""

from unittest.loader import defaultTestLoader

from plainbox.impl import get_plainbox_dir


def load_unit_tests():
    """
    Load all unit tests and return a TestSuite object
    """
    # Discover all unit tests. By simple convention those are kept in
    # python modules that start with the word 'test_' .
    return defaultTestLoader.discover(get_plainbox_dir())


def load_integration_tests():
    """
    Load all integration tests and return a TestSuite object
    """
    # Discover all integration tests. By simple convention those are kept in
    # python modules that start with the word 'integration_' .
    return defaultTestLoader.discover(
        get_plainbox_dir(), pattern="integration_*.py")


def test_suite():
    """
    Test suite function used by setuptools test loader.

    Uses unittest test discovery system to get a list of test cases defined
    inside plainbox. See setup.py setup(test_suite=...) for a matching entry
    """
    return load_unit_tests()
