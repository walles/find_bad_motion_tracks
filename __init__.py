# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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

from typing import cast, List, Dict, Iterable
from dataclasses import dataclass

from bpy.types import MovieTrackingMarkers, MovieTrackingTrack

bl_info = {
    "name": "Find Bad Tracks",
    "author": "Johan Walles",
    "description": "",
    "blender": (2, 93, 1),
    "version": (0, 0, 1),
    "location": "Clip Editor > Tools > Track > Find Bad Tracks",
    "warning": "",
    "category": "Video Tools",
}

FIND_BAD_TRACKS = "Find Bad Tracks"


@dataclass
class TrackMovement:
    track: MovieTrackingTrack
    frame0: int
    frame1: int
    dx: float
    dy: float


@dataclass
class Badness:
    amount: float
    frame: int


class MovementRange:
    def __init__(self, movements: List[TrackMovement]) -> None:
        # Take the median of all movements between previous and this frame,
        # for X and Y independently.
        dx_median = statistics.median(map(lambda movement: movement.dx, movements))
        dy_median = statistics.median(map(lambda movement: movement.dy, movements))

        # For a 10 item list, this will be 8
        percentile_count = (len(movements) * 4) // 5
        assert 0 < percentile_count < len(movements)

        # For a 10 item list, with indices 0-9, this will be 7
        percentile_index = percentile_count - 1

        dx_distance = sorted(
            map(lambda movement: abs(movement.dx - dx_median), movements)
        )[percentile_index]
        dy_distance = sorted(
            map(lambda movement: abs(movement.dy - dy_median), movements)
        )[percentile_index]

        self.dx_median = dx_median
        self.dy_median = dy_median
        self.dx_distance = dx_distance
        self.dy_distance = dy_distance

    def compute_badness_score(self, movement: TrackMovement) -> float:
        # Figure out how much this track moved compared to the median and the
        # movement wiggle room, on X and Y independently.
        x_badness = abs(movement.dx - self.dx_median) / self.dx_distance
        y_badness = abs(movement.dy - self.dy_median) / self.dy_distance
        return max(x_badness, y_badness)


class OP_Tracking_find_bad_tracks(bpy.types.Operator):
    """
    Identify bad tracks by looking at how they move relative to other tracks.

    For example, if all tracks move left in a frame, except one that moves
    right, the moving-right track is likely bad and a human should inspect it.
    """

    bl_idname = "tracking.find_bad_tracks"
    bl_label = FIND_BAD_TRACKS

    @classmethod
    def poll(cls, context):
        # FIXME: Return true if we have any tracks, this method is a duplicate!
        return True

    def execute(self, context: bpy.types.Context):
        spaces = cast(bpy.types.AreaSpaces, context.area.spaces)
        active = cast(bpy.types.SpaceClipEditor, spaces.active)
        clip = active.clip

        # For each clip frame except the first...
        first_frame_index = clip.frame_start
        last_frame_index = clip.frame_start + clip.frame_duration - 1
        print(f"Clip goes from frame {first_frame_index} to {last_frame_index}")

        # Map track names to badness scores
        badnesses: Dict[str, Badness] = {}

        for frame_index in range(first_frame_index + 1, last_frame_index):
            movements: List[TrackMovement] = []

            tracks = cast(List[MovieTrackingTrack], clip.tracking.tracks)
            for track in tracks:
                markers = cast(MovieTrackingMarkers, track.markers)

                previous_marker = markers.find_frame(frame_index - 1)
                if previous_marker is None or previous_marker.mute:
                    continue

                marker = markers.find_frame(frame_index)
                if marker is None or marker.mute:
                    continue

                # How much did this track move X and Y since the previous frame?
                dx = marker.co[0] - previous_marker.co[0]
                dy = marker.co[1] - previous_marker.co[1]
                movements.append(
                    TrackMovement(track, frame_index - 1, frame_index, dx, dy)
                )

            if not movements:
                # No markers for this frame
                continue

            movement_range = MovementRange(movements)

            # For each track, keep track of the worst badness score so far, for
            # X and Y independently.
            for movement in movements:
                badness_score = movement_range.compute_badness_score(movement)

                if movement.track.name not in badnesses:
                    badnesses[movement.track.name] = Badness(
                        badness_score, movement.frame1
                    )
                    continue

                old_badness = badnesses[movement.track.name]
                if old_badness.amount > badness_score:
                    continue

                badnesses[movement.track.name] = Badness(badness_score, movement.frame1)

        # FIXME: Put this information in the UI
        for track_name, badness in sorted(
            badnesses.items(), key=lambda item: item[1].amount
        ):
            print(
                f"{track_name} badness={badness.amount:5.2f} at frame {badness.frame:3d}"
            )

        return {"FINISHED"}


class TRACKING_PT_FindBadTracksPanel(bpy.types.Panel):
    bl_label = FIND_BAD_TRACKS
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Track"

    @classmethod
    def poll(cls, context):
        # FIXME: Return true if we have any tracks, this method is a duplicate!
        return True

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("tracking.find_bad_tracks")


classes = (
    OP_Tracking_find_bad_tracks,
    TRACKING_PT_FindBadTracksPanel,
)
register, unregister = bpy.utils.register_classes_factory(classes)


if __name__ == "__main__":
    register()
