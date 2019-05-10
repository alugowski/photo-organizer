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

import os
import shutil
from datetime import datetime

from .exif import get_interesting_exif_tags


DATE_FORMAT = "%Y-%m-%d"

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

INTERESTING_EXTENSIONS = {e.lstrip(".") for e in PHOTO_EXTENSIONS.union(VIDEO_EXTENSIONS)}


class Bundle:
    """
    Class that bundles multiple files together to be treated as one.

    Particularly useful when dealing with DSLR photos, since they can have a RAW, a JPEG, and possibly a .XMP sidecar
    file (from Adobe converters). Renaming one should rename the others, too.
    """
    def __init__(self, path):
        self.paths = [path]
        self.base, extension = os.path.splitext(path)
        self.extensions = [extension.lstrip(".")]
        self.interesting_exif = None

    def add_maybe(self, path):
        """
        Add `path` to this bundle, but only if it fits.

        A path fits if it only differs by extension.

        :param path: path to maybe add
        :return: True if `path` fits and was successfully added. False if `path` doesn't fit.
        """
        fn, extension = os.path.splitext(path)
        if fn != self.base:
            return False

        self.paths.append(path)
        self.extensions.append(extension.lstrip("."))
        return True

    def __repr__(self):
        if len(self.paths) == 1:
            return self.paths[0]

        return "{base}.[{extensions}]".format(base=self.base, extensions=",".join(self.extensions))

    def is_interesting(self):
        """
        :return: True if any of the files are a photo or video
        """
        return any(e.lower() in INTERESTING_EXTENSIONS for e in self.extensions)

    def move(self, destination):
        """
        Move all files in this bundle to `destination`.

        :param destination: directory to move to.
        """
        for path in self.paths:
            shutil.move(path, destination)

    def copy(self, destination):
        """
        Copy all files in this bundle to `destination`.

        :param destination: directory to copy to.
        """
        for path in self.paths:
            shutil.copy(path, destination)

    def get_oldest_mtime(self):
        """
        :return: unix timestamp of the oldest file in this bundle
        """
        return min([os.path.getmtime(path) for path in self.paths])

    def _ensure_exif(self):
        """
        Find and read EXIF data, if there's an supported file in this bundle.

        Result is stored in `self.interesting_exif` and only populated on first call. OK to call multiple times.
        """
        if self.interesting_exif is None:
            # find a file that has EXIF
            for path in self.paths:
                _, extension = os.path.splitext(path)
                extension = extension.lower()
                if extension in [".jpg", ".jpeg"]:
                    self.interesting_exif = get_interesting_exif_tags(path)
                    return

            # no supported files in this bundle
            self.interesting_exif = {}

    def get_shooting_time(self):
        """
        :return: unix timestamp of the original shooting date as specified in EXIF data, or None if not found
        """

        self._ensure_exif()

        return self.interesting_exif.get("shooting_date_unix", None)

    def get_date(self):
        """
        :return: a formatted date for this bundle
        """
        dt = datetime.fromtimestamp(self.get_shooting_time() or self.get_oldest_mtime())
        return dt.strftime(DATE_FORMAT)

    def get_lat_long(self):
        """
        :rtype: tuple[float, float]
        :return: latitude, longitude pair as specified in EXIF data, or None if not found
        """
        self._ensure_exif()

        return self.interesting_exif.get("lat_long", None)
