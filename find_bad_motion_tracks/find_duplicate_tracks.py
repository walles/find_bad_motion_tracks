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

from typing import Iterable, cast, List, Dict, Optional, Tuple

from bpy.types import (
    MovieClip,
    MovieTrackingTrack,
    MovieTrackingMarkers,
)

# If two points are further apart than this many percent of the image dimensions
# they are not dups (at least not in this frame).
DUP_MAXDIST_PERCENT = 0.5


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


def find_duplicate_tracks(clip: MovieClip) -> Iterable[Duplicate]:
    # For each clip frame...
    first_frame_index = clip.frame_start
    last_frame_index = clip.frame_start + clip.frame_duration - 1

    # Map track names to badness scores
    dups: Dict[Tuple[str, str], Duplicate] = {}

    for frame_index in range(first_frame_index, last_frame_index + 1):
        track_coordinates = []

        tracks = cast(List[MovieTrackingTrack], clip.tracking.tracks)
        for track in tracks:
            markers = cast(MovieTrackingMarkers, track.markers)
            marker = markers.find_frame(frame_index)
            if marker is None or marker.mute:
                continue

            x = marker.co[0]
            y = marker.co[1]

            track_coordinates.append((x, y, track.name))

        for x1, y1, track1_name in track_coordinates:
            for x2, y2, track2_name in track_coordinates:
                if track1_name >= track2_name:
                    # Require alphabetic order to avoid duplicates
                    #
                    # FIXME: It should be possible to make these nested loops
                    # twice as fast by ensuring the tracks are sorted in name
                    # order and doing "break" here under the right
                    # circumstances.
                    continue

                dx = x2 - x1
                dy = y2 - y1
                dist2 = dx * dx + dy * dy

                key = (track1_name, track2_name)
                dup = dups.get(key)
                if dup is None:
                    dup = Duplicate(track1_name, track2_name, frame_index, dist2)
                    dups[key] = dup
                dup.update(frame_index, dist2)

    # Return the track pairs that come close enough at some point
    return filter(lambda dup: dup.are_dups(), dups.values())
