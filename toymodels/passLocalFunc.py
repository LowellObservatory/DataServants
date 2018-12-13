# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 15 Mar 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import passedJunk


def f1(idict, arg1, arg2=None, debug=False):
    print(idict)
    print(arg1)
    print(arg2)


if __name__ == "__main__":
    thing1 = 'radio'
    thing2 = 'beees'
    idict = {"Comp1": 42, "Comp2": "coconuts"}
    passedJunk.function1(f1, idict, thing1, f1a2=thing2)
