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

import logging
import os
from datetime import datetime

from .bundle import Bundle

ANDROID_PHOTO_LOCATIONS = ["DCIM", "Pictures"]


def get_latest_mtime(path):
    """
    Return the newest modified date of any file in the path
    :param path: path to check recursively
    :return: unix timestamp, possibly an old one if the path is empty
    """
    mtime = 0
    for (dirpath, _, filenames) in os.walk(path):
        for f in filenames:
            photo_path = os.path.join(path, dirpath, f)
            mtime = max(mtime, os.path.getmtime(photo_path))
    return mtime


def get_android_locations(source_dir):
    """
    :param source_dir: directory of Android storage root
    :return: directories that should be scanned recursively
    """
    return [os.path.join(source_dir, subdir) for subdir in ANDROID_PHOTO_LOCATIONS]


def get_bundles(directory, filenames):
    """
    Group files into Bundles.

    :param directory: base directory
    :param filenames: files in `directory`
    :rtype: Iterator[:class:`Bundle`]
    :return: an iterator of Bundles
    """
    filenames = sorted(filenames)

    cur_bundle = None
    for fn in filenames:
        path = os.path.join(directory, fn)

        if cur_bundle is None:
            # first file starts a bundle
            cur_bundle = Bundle(path)
            continue

        # try adding to the current bundle
        if not cur_bundle.add_maybe(path):
            # does not fit, need a new bundle
            yield cur_bundle
            cur_bundle = Bundle(path)

    # yield last bundle
    if cur_bundle is not None:
        yield cur_bundle


def get_interesting_bundles(directory, filenames, min_mtime):
    """
    Group files into Bundles, then filter only the interesting ones.

    :param directory: base directory
    :param filenames: files in `directory`
    :param min_mtime: minimum Unix timestamp
    :rtype: Iterator[:class:`Bundle`]
    :return: an iterator of Bundles
    """

    for bundle in get_bundles(directory, filenames):
        # filter out bundles that don't have a photo/video
        if not bundle.is_interesting():
            continue

        # filter out bundles that are too old
        bundle_ts = bundle.get_oldest_mtime()
        if bundle_ts <= min_mtime:
            continue

        yield bundle


def get_photo_bundles(source_dirs, recursive, newer_only, dest_dir):
    """
    :rtype: Iterator[:class:`Bundle`]
    :return: generator of Bundles to be processed
    """
    # find the minimum mtime to filter files by
    min_mtime = get_latest_mtime(dest_dir) if newer_only else 0

    # find photos in the given source dirs
    for source_dir in source_dirs:
        logging.info("Reading {path} {rec}{mtime}"
                     .format(path=source_dir,
                             rec=("recursively" if recursive else "not recursively"),
                             mtime=", looking for files newer than {}".format(datetime.fromtimestamp(min_mtime))
                                   if min_mtime > 0 else ""))

        if recursive:
            for (subdir, _, filenames) in os.walk(source_dir):
                current_dir = os.path.join(source_dir, subdir)

                yield from get_interesting_bundles(current_dir, filenames, min_mtime=min_mtime)
        else:
            # not recursive
            filenames = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
            yield from get_interesting_bundles(source_dir, filenames, min_mtime=min_mtime)
