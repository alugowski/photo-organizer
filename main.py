#!/usr/bin/env python3
#
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
Automatically organize photos from unlabeled sources such as phone picture folders.
"""

import argparse

from photo_organizer import scanner
from photo_organizer import organizer


def get_logging_format_string():
    return '%(asctime)s %(levelname)s: %(message)s'


def setup_basic_logging():
    import logging
    import sys

    logging.basicConfig(format=get_logging_format_string(),
                        stream=sys.stdout,
                        level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-r', '--recursive', help='Search source directory recursively',
                        default=False, action="store_true")

    parser.add_argument('--android-root', help="Source is an Android storage root, check subdirectories where "
                                               "Android puts photos: " + ", ".join(scanner.ANDROID_PHOTO_LOCATIONS),
                        default=False, action="store_true")

    parser.add_argument('-m', '--move', help='Move files instead of copying.',
                        default=False, action="store_true")

    parser.add_argument('-n', '--dry-run', help='Print actions but do not execute them.',
                        default=False, action="store_true")

    parser.add_argument('-f', '--full', help='By default only source files newer than the newest file in `dest_dir` '
                                             'are scanned. If set to true, scan all files regardless.',
                        default=False, action="store_true")

    parser.add_argument('--min-dir-count', type=int, default=3,
                        help='Minimum number of photos to share same toplevel description '
                             'to be placed in their own subdirectory. -1 to never place in subdirectories.')

    parser.add_argument('source_dir',
                        help="Location of photos to organize")

    parser.add_argument('dest_dir', default=".",
                        help="Location of where to place organized photos")

    return parser.parse_args()


def main():
    setup_basic_logging()
    args = parse_args()

    # get configuration
    recursive = args.recursive
    newer_only = not args.full
    dry_run = args.dry_run

    # if source_dir is an Android root then construct all the places Android puts photos
    if args.android_root:
        source_dirs = scanner.get_android_locations(args.source_dir)
        recursive = True
    else:
        source_dirs = [args.source_dir]

    # scan source dir
    bundles = scanner.get_photo_bundles(source_dirs=source_dirs,
                                        recursive=recursive,
                                        newer_only=newer_only,
                                        dest_dir=args.dest_dir)

    # organize
    dirs = organizer.organize_into_directories(bundles=bundles, min_dir_count=args.min_dir_count)

    # move/copy files
    for d, d_bundles in dirs.items():
        organizer.move_photos(args.dest_dir, d, bundles=d_bundles, move=args.move, dry_run=dry_run)


if __name__ == "__main__":
    main()
