# This file is part of Checkbox.
#
# Copyright 2013 Canonical Ltd.
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
:mod:`plainbox.impl.test_color`
===============================

Test definitions for plainbox.impl.color
"""

from unittest import TestCase

from plainbox.impl.color import ansi_on, ansi_off


class ColorTests(TestCase):

    def test_smoke(self):
        self.assertEqual(ansi_on.f.RED, "\033[31m")
        self.assertEqual(ansi_off.f.RED, "")
        self.assertEqual(ansi_on.b.RED, "\033[41m")
        self.assertEqual(ansi_off.b.RED, "")
        self.assertEqual(ansi_on.s.BRIGHT, "\033[1m")
        self.assertEqual(ansi_off.s.BRIGHT, "")
