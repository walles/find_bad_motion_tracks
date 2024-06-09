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

import bpy
import statistics

from dataclasses import dataclass

from typing import Iterable, cast, List, Dict, Optional, Tuple

from bpy.types import (
    MovieClip,
    MovieTrackingTrack,
    MovieTrackingMarker,
    MovieTrackingMarkers,
)

# If two points are further apart than this many percent of the image dimensions
# they are not dups (at least not in this frame).
DUP_MAXDIST_PERCENT = 0.5

# Anything within this percentile will get a badness score <= 1
PERCENTILE = 80


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


class BadnessCalculator:
    def __init__(self, movements: List[TrackWithFloat]) -> None:
        # Take the median of all numbers.
        #
        # FIXME: Should we give higher weights to locked tracks? Since a human
        # has likely locked them because those tracks are known good?
        median = statistics.median(map(lambda movement: movement.number, movements))

        # With PERCENTILE at 80, for a 10 item list, this will be 8
        percentile_count = (len(movements) * PERCENTILE) // 100
        assert 0 < percentile_count < len(movements)

        # With PERCENTILE at 80, for a 10 item list, with indices 0-9, this will
        # be 7, skipping the two last ones.
        percentile_index = percentile_count - 1

        distance = sorted(
            map(lambda movement: abs(movement.number - median), movements)
        )[percentile_index]

        self.median = median
        self.distance = distance

    def compute_badness_score(self, movement: TrackWithFloat) -> float:
        # Figure out how much this track moved compared to the median and the
        # movement wiggle room.
        if self.distance == 0:
            return 0.0

        return abs(movement.number - self.median) / self.distance


def update_badnesses(
    badnesses: Dict[str, Badness], movements: List[TrackWithFloat]
) -> None:
    if not movements:
        # Nothing to see here, move along. Also, the median() call in the
        # BadnessCalculator constructor throws an exception if called with no
        # data.
        return

    if len(movements) < 4:
        # To detect outliers we want a median, with one track on each side to
        # set the baseline, plus a fourth track that is potentially outlying.
        # With fewer tracks than that the badness score becomes too uncertain.
        return

    # For each track, keep track of the worst badness score so far
    badness_calculator = BadnessCalculator(movements)
    for movement in movements:
        if movement.track.lock:
            # Assume locked tracks have been vetted by a human and that
            # they are perfect.
            continue

        badness_score = badness_calculator.compute_badness_score(movement)

        if movement.track.name not in badnesses:
            badnesses[movement.track.name] = Badness(
                badness_score, movement.blame_frame
            )
            continue

        old_badness = badnesses[movement.track.name]
        if old_badness.amount > badness_score:
            continue

        badnesses[movement.track.name] = Badness(badness_score, movement.blame_frame)


def shape_change_amount(
    previous_marker: MovieTrackingMarker, marker: MovieTrackingMarker
) -> float:
    """How much did the corners of the marker move between these frames?"""
    assert len(previous_marker.pattern_corners) == 4
    assert len(marker.pattern_corners) == 4

    dx = 0.0
    dy = 0.0
    for i in range(0, 4):
        previous_x: float = previous_marker.pattern_corners[i][0]
        previous_y: float = previous_marker.pattern_corners[i][1]
        x: float = marker.pattern_corners[i][0]
        y: float = marker.pattern_corners[i][1]
        dx += abs(x - previous_x)
        dy += abs(y - previous_y)

    return dx + dy


def combine_badnesses(*args: Dict[str, Badness]) -> Dict[str, Badness]:
    """
    Scale each collection so that the 80th percentile is at 1.0. Then for
    each track mentioned, pick the highest datapoint out of any collection.
    """

    with_percentile_scores: List[Tuple[Dict[str, Badness], float]] = []
    for track_to_badness in args:
        if len(track_to_badness) < 1:
            continue
        percentile = sorted(
            map(lambda badness: badness.amount, track_to_badness.values())
        )[(len(track_to_badness) * PERCENTILE) // 100]

        with_percentile_scores.append((track_to_badness, percentile))

    # Join up the with_percentile_scores tuples into a resulting dict
    combined: Dict[str, Badness] = {}
    for badnesses, percentile in with_percentile_scores:
        for track, badness in badnesses.items():
            to_beat_amount = 0.0
            to_beat = combined.get(track)
            if to_beat is not None:
                to_beat_amount = to_beat.amount

            adjusted_amount = badness.amount / percentile
            if adjusted_amount > to_beat_amount:
                combined[track] = Badness(adjusted_amount, badness.frame)

    return combined


def find_bad_tracks(clip: MovieClip) -> Dict[str, Badness]:
    # For each clip frame except the first...
    first_frame_index = clip.frame_start
    last_frame_index = clip.frame_start + clip.frame_duration - 1

    # Map track names to badness scores
    dx_badnesses: Dict[str, Badness] = {}
    dy_badnesses: Dict[str, Badness] = {}
    ddx_badnesses: Dict[str, Badness] = {}
    ddy_badnesses: Dict[str, Badness] = {}

    # Map track names to marker shape change amounts
    shape_badnesses: Dict[str, Badness] = {}

    for frame_index in range(first_frame_index + 1, last_frame_index):
        dx_list: List[TrackWithFloat] = []
        dy_list: List[TrackWithFloat] = []
        ddx_list: List[TrackWithFloat] = []
        ddy_list: List[TrackWithFloat] = []

        tracks = cast(List[MovieTrackingTrack], clip.tracking.tracks)
        for track in tracks:
            markers = cast(MovieTrackingMarkers, track.markers)

            previous_marker = markers.find_frame(frame_index - 1)
            if previous_marker is None or previous_marker.mute:
                continue

            marker = markers.find_frame(frame_index)
            if marker is None or marker.mute:
                continue

            highest_shape_change = shape_badnesses.get(track.name, None)
            shape_change = shape_change_amount(previous_marker, marker)
            if (
                highest_shape_change is None
                or shape_change > highest_shape_change.amount
            ):
                shape_badnesses[track.name] = Badness(shape_change, frame_index)

            # How much did this track move X and Y since the previous frame?
            dx = marker.co[0] - previous_marker.co[0]
            dy = marker.co[1] - previous_marker.co[1]
            dx_list.append(TrackWithFloat(track, dx, frame_index))
            dy_list.append(TrackWithFloat(track, dy, frame_index))

            previous_previous_marker = markers.find_frame(frame_index - 2)
            if previous_previous_marker is None or previous_previous_marker.mute:
                continue

            previous_dx = previous_marker.co[0] - previous_previous_marker.co[0]
            previous_dy = previous_marker.co[1] - previous_previous_marker.co[1]
            ddx = dx - previous_dx
            ddy = dy - previous_dy
            ddx_list.append(TrackWithFloat(track, ddx, frame_index))
            ddy_list.append(TrackWithFloat(track, ddy, frame_index))

        update_badnesses(dx_badnesses, dx_list)
        update_badnesses(dy_badnesses, dy_list)
        update_badnesses(ddx_badnesses, ddx_list)
        update_badnesses(ddy_badnesses, ddy_list)

    return combine_badnesses(
        dx_badnesses, dy_badnesses, ddx_badnesses, ddy_badnesses, shape_badnesses
    )


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


def get_active_clip(context: bpy.types.Context):
    spaces = cast(bpy.types.AreaSpaces, context.area.spaces)
    active = cast(bpy.types.SpaceClipEditor, spaces.active)
    return active.clip
