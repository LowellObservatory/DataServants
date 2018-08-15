# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 2 Mar 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

from dataservants import yvette


if __name__ == "__main__":
    # Yvette has no configuration file, and allows multiple
    #   processes to run simultaneously if desired. That means
    #   we're not using the ligmos.workers.toServeMan constructor
    #   and instead skipping right into the meat of things.
    # NOTE: beginTidying returns a json object of results, but
    #   since it's printed over there I'm ignoring it here.
    yvette.tidy.beginTidying()
