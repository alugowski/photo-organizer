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
Routines for extracting useful EXIF tags from JPEG files.
"""

from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
GPS_REQUIRED_KEYS = ("GPSLatitude", "GPSLongitude", "GPSLatitudeRef", "GPSLongitudeRef")


def rational_dms_to_decimal(dms, reference):
    """
    Convert EXIF GPSInfo-formatted latitude or longitude into a decimal latitude or longitude.

    :param dms: 3-tuple of decimal, minutes, seconds, each specified as a 2-tuple of numerator, denominator
    :type dms: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]
    :param reference: one of [N, S, E, W]
    :rtype: float
    :return: a decimal version of dms
    """
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0

    if reference in ('S', 'W'):
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 6)


def get_coordinates(gps_info):
    """
    Extract latitude, longitude from EXIF GPSInfo struct.

    :param dict gps_info: GPSInfo structure. Must have all keys listed in GPS_REQUIRED_KEYS
    :rtype: tuple[float, float]
    :return: tuple of latitude, longitude
    """
    lat = rational_dms_to_decimal(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
    lon = rational_dms_to_decimal(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])

    return lat, lon


def get_labeled_exif(path, tag_whitelist=None):
    """
    Extract EXIF information and present it in a human-workable format.

    :param path: path to JPEG file
    :param tag_whitelist: if not None, only return tags in this collection
    :rtype: dict
    :return: EXIF in dictionary form. Empty dictionary if no EXIF found.
    """
    image = Image.open(path)
    image.verify()
    # noinspection PyProtectedMember
    exif = image._getexif()

    if not exif:
        return {}

    # convert numeric tags to labeled strings
    labeled_exif = {TAGS.get(key): value for key, value in exif.items()
                    if tag_whitelist is None or TAGS.get(key) in tag_whitelist}

    # GPSInfo is a nested dictionary, decode it too
    gps_info = labeled_exif.get("GPSInfo")
    if gps_info:
        labeled_gps_info = {GPSTAGS.get(key): value for key, value in gps_info.items()}
        labeled_exif["GPSInfo"] = labeled_gps_info

    return labeled_exif


def get_interesting_exif_tags(path):
    """
    Get EXIF tags that are useful for photo organization.

    :param path: path to JPEG file
    :return: dictionary of useful info, empty dict if none found
    """
    exif = get_labeled_exif(path, tag_whitelist=("DateTimeOriginal", "GPSInfo"))

    ret = {}

    # pick out the original shooting date
    shooting_date = exif.get("DateTimeOriginal")
    if shooting_date:
        dt = datetime.strptime(shooting_date, EXIF_DATETIME_FORMAT)
        ret["shooting_date"] = dt
        ret["shooting_date_unix"] = dt.timestamp()

    # pick up the latitude and longitude
    gps_info = exif.get("GPSInfo")
    if gps_info and all(k in gps_info for k in GPS_REQUIRED_KEYS):
        ret["lat_long"] = get_coordinates(gps_info)

    return ret
