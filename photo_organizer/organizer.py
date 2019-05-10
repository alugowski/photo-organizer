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
from collections import defaultdict

from .geo import get_best_static_label


def get_directory(bundle):
    """
    Get the subdirectory that this bundle should be placed in

    :param bundle: photo bundle
    :return: subdirectory name
    """
    parts = []

    # look up date
    path_date = bundle.get_date()
    parts.append(path_date)

    # look up geo
    lat_long = bundle.get_lat_long()
    if lat_long:
        geo_label = get_best_static_label(lat_long)
        parts.append(geo_label)

    return " - ".join(parts)


def organize_into_directories(bundles, min_dir_count):
    """
    Arrange the bundles into directories.

    :param bundles: bundles to organize
    :param min_dir_count: minimum number of bundles for a directory to be used.
    :rtype: dict
    :return: mapping of directory -> list of bundles
    """
    if min_dir_count < 0:
        # user requested no subdirectories
        return {"": list(bundles)}

    # find subdirectories based on identifiable features
    dirs = defaultdict(list)

    # get the directory for each path
    for bundle in bundles:
        fdir = get_directory(bundle)
        dirs[fdir].append(bundle)

    # collapse according to arguments
    ret = {}
    for d, bundles in dirs.items():
        if len(bundles) >= min_dir_count:
            ret[d] = bundles
        else:
            # too few files in this target directory, put them in the root
            if "" not in ret:
                ret[""] = []
            ret[""].extend(bundles)
    return ret


def make_dir(d, dry_run):
    """
    Ensure directory d exists. Respects dry-run.

    :param d: directory to create
    :param dry_run: if True, only log
    """
    if not os.path.isdir(d):
        logging.info("Creating " + d)
        if not dry_run:
            os.mkdir(d)


def move_photos(dest_dir, subdir, bundles, move, dry_run):
    """
    Move photo bundles.

    :param dest_dir: destination base directory
    :param subdir: subdirectory
    :param bundles: bundles to move
    :param move: if True then move files, if False then copy
    :param dry_run: if True, only log
    """

    final_dir = os.path.join(dest_dir, subdir)

    make_dir(final_dir, dry_run)

    action = "Moving" if move else "Copying"

    for bundle in bundles:
        logging.info("{} {} to {}".format(action, bundle, final_dir))
        if not dry_run:
            if move:
                bundle.move(final_dir)
            else:
                bundle.copy(final_dir)
