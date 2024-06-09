# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from dataclasses import dataclass

from typing import Optional

from bpy.types import (
    MovieTrackingTrack,
)

# If two points are further apart than this many percent of the image dimensions
# they are not dups (at least not in this frame).
DUP_MAXDIST_PERCENT = 0.5


@dataclass
class TrackWithFloat:
    track: MovieTrackingTrack
    number: float
    blame_frame: int


@dataclass
class Badness:
    amount: float
    frame: int


class Duplicate:
    dup_maxdist_fraction = DUP_MAXDIST_PERCENT / 100.0
    dup_maxdist2 = dup_maxdist_fraction * dup_maxdist_fraction

    def __init__(
        self, track1_name: str, track2_name: str, frame_number: int, distance2: float
    ) -> None:
        self.track1_name = track1_name
        self.track2_name = track2_name
        self.maxdist2 = distance2

        self.first_common_frame = frame_number
        self.last_common_frame = frame_number

        self.first_overlapping_frame: Optional[int] = None
        self.last_overlapping_frame: Optional[int] = None

        self.update(frame_number, distance2)

    def update(self, frame_number: int, distance2: float) -> None:
        if distance2 > self.maxdist2:
            self.maxdist2 = distance2

        self.last_common_frame = frame_number

        if distance2 > Duplicate.dup_maxdist2:
            return

        # Tracks are overlapping
        if self.first_overlapping_frame is None:
            self.first_overlapping_frame = frame_number
        self.last_overlapping_frame = frame_number

    def are_dups(self) -> bool:
        return self.first_overlapping_frame is not None

    def most_interesting_frame(self) -> int:
        assert self.first_overlapping_frame is not None
        assert self.last_overlapping_frame is not None

        if self.last_overlapping_frame < self.last_common_frame:
            # We stop overlapping and drift apart
            return self.last_overlapping_frame

        return self.first_overlapping_frame
