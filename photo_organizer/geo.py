# Copyright (C) 2019 Adam Lugowski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Routines for getting geographical labels from lat/long.
"""

import reverse_geocode
import geopy.distance


def get_distance(coords1, coords2):
    # use this later to set up clustering.
    return geopy.distance.distance(coords1, coords2).meters


def get_best_static_label(coordinates):
    """
    Get the best label we can from a static database.

    :param tuple[float, float] coordinates: a tuple of (latitude, longitude)
    :rtype: str
    :return: a city string
    """
    loc = reverse_geocode.search((coordinates,))
    if not loc:
        return None

    loc = loc[0]

    if "city" in loc:
        return loc["city"]

    if "country" in loc:
        return loc["country"]

    return None


def get_geo_label(coordinates):
    """
    Get the best geographic label for the given coordinates.

    :param tuple[float, float] coordinates: a tuple of (latitude, longitude)
    :rtype: str
    :return: a string to describe the lat/long, or None
    """
    return get_best_static_label(coordinates)
