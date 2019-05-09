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
import logging
import os
import shutil

from collections import defaultdict
from datetime import datetime

DATE_FORMAT = "%Y-%m-%d"

ANDROID_PHOTO_LOCATIONS = ["DCIM", "Pictures"]
PHOTO_EXTENSIONS_STR = """
.jpg, .jpeg,
.3fr,
.ari, .arw,
.bay,
.crw, .cr2, .cr3,
.cap,
.data, .dcs, .dcr, .dng,
.drf,
.eip, .erf,
.fff,
.gpr,
.iiq,
.k25, .kdc,
.mdc, .mef, .mos, .mrw,
.nef, .nrw,
.obm, .orf,
.pef, .ptx, .pxn,
.r3d, .raf, .raw, .rwl, .rw2, .rwz,
.sr2, .srf, .srw,
.tif, .tiff,
.x3f"""
PHOTO_EXTENSIONS = {ext.strip() for ext in PHOTO_EXTENSIONS_STR.split(",")}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

EXTENSIONS = PHOTO_EXTENSIONS.union(VIDEO_EXTENSIONS)


def get_logging_format_string():
    return '%(asctime)s %(filename)s:%(lineno)s - %(funcName)s() %(levelname)s: %(message)s'


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
                                               "Android puts photos: " + ", ".join(ANDROID_PHOTO_LOCATIONS),
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


def get_latest_mtime(path):
    """
    Return the newest modified date of any file in the path
    :param path: path to check recursively
    :return: unix timestamp, possibly an old one if the path is empty
    """
    mtime = 0
    for (dirpath, dirnames, filenames) in os.walk(path):
        for f in filenames:
            photo_path = os.path.join(path, dirpath, f)
            mtime = max(mtime, os.path.getmtime(photo_path))
    return mtime


def is_interesting(path, min_mtime):
    """
    :param path: path to a file
    :param min_mtime: minimum modified time
    :return: True iff `path` refers to a photo or video file and is newer than `min_mtime`
    """
    # make sure the file has the right extension
    _, extension = os.path.splitext(path)
    if extension.lower() not in EXTENSIONS:
        return False

    # check for time
    mtime = os.path.getmtime(path)
    return mtime > min_mtime


def get_sidecars(path):
    """
    :param path: filename
    :return: a set of files that should be moved together with this file. Think RAW files and Adobe's .XMP sidecars
    """
    return [path]


def get_photo_files(args):
    """
    :param args: parsed argsparse object
    :return: generator of photos to be processed
    """
    source_dir = args.source_dir
    recursive = args.recursive

    # find the minimum mtime to filter files by
    if args.full:
        min_mtime = 0
    else:
        min_mtime = get_latest_mtime(args.dest_dir)

    # if Android, then construct all the places Android puts photos
    if args.android_root:
        sources = [os.path.join(source_dir, subdir) for subdir in ANDROID_PHOTO_LOCATIONS]
        recursive = True
    else:
        sources = [source_dir]

    # find photos in the given source dirs
    for path in sources:
        logging.info("Reading {path} {rec}{mtime}"
                     .format(path=path,
                             rec=("recursively" if recursive else "not recursively"),
                             mtime=", looking for files newer than {}".format(datetime.fromtimestamp(min_mtime))
                                   if min_mtime > 0 else ""))

        if recursive:
            for (dirpath, dirnames, filenames) in os.walk(path):
                for f in filenames:
                    photo_path = os.path.join(path, dirpath, f)
                    if is_interesting(photo_path, min_mtime):
                        yield photo_path
        else:
            # not recursive
            for f in os.listdir(path):
                photo_path = os.path.join(path, f)

                # only files
                if not os.path.isfile(photo_path):
                    continue

                # check for interesting
                if is_interesting(photo_path, min_mtime):
                    yield photo_path


def get_date(path):
    """
    :param path: file path
    :return: a formatted date for this path
    """
    # TODO: potentially get original shooting date from EXIF:
    # https://stackoverflow.com/questions/23064549/get-date-and-time-when-photo-was-taken-from-exif-data-using-pil

    dt = datetime.fromtimestamp(os.path.getmtime(path))
    return dt.strftime(DATE_FORMAT)


def get_directory(path):
    """
    Get the subdirectory that this photo should be placed in

    :param path: photo path
    :return: subdirectory name
    """
    path_date = get_date(path)
    return " - ".join([path_date])


def organize_into_directories(args, paths):
    if args.min_dir_count < 0:
        # user requested no subdirectories
        return {"": list(paths)}

    # find subdirectories based on identifiable features
    dirs = defaultdict(list)

    # get the directory for each path
    for path in paths:
        fdir = get_directory(path)
        dirs[fdir].append(path)

    # collapse according to arguments
    ret = {}
    for d, paths in dirs.items():
        if len(paths) >= args.min_dir_count:
            ret[d] = paths
        else:
            if "" not in ret:
                ret[""] = []
            ret[""].extend(paths)
    return ret


def make_dir(args, d):
    """
    Ensure directory d exists. Respects dry-run.

    :param args: parsed user arguments
    :param d: directory to create
    """
    if not os.path.isdir(d):
        logging.info("Creating " + d)
        if not args.dry_run:
            os.mkdir(d)


def move_photos(args, d, paths):
    """
    Move photos. Respects dry-run.

    :param args: parsed user arguments
    :param d: directory to move to
    :param paths: source paths to move
    """
    final_dir = os.path.join(args.dest_dir, d)

    make_dir(args, final_dir)

    action = "Moving" if args.move else "Copying"

    for path in paths:
        logging.info("{} {} to {}".format(action, path, final_dir))
        if not args.dry_run:
            if args.move:
                shutil.move(path, final_dir)
            else:
                shutil.copy2(path, final_dir)


def main():
    setup_basic_logging()
    args = parse_args()

    # TODO: work in terms of bundles instead of individual files.
    #  A bundle can be a set of files with the same name but different extension. Think NEF, JPEG, XMP

    dirs = organize_into_directories(args, get_photo_files(args))

    for d, paths in dirs.items():
        move_photos(args, d, paths)


if __name__ == "__main__":
    main()
