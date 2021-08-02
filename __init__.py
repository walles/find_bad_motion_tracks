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
    "description": "Highlight motion tracks that move in suspicious directions",
    "blender": (2, 93, 1),
    "version": (0, 0, 1),
    "location": "Clip Editor > Tools > Track > Find Bad Tracks",
    "warning": "",
    "tracker_url": "https://github.com/walles/find_bad_motion_tracks/issues",
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


class BadnessItem(bpy.types.PropertyGroup):
    # FIXME: How do we make all of these read-only?

    track: bpy.props.StringProperty(  # type: ignore
        name="Track",
        options={"SKIP_SAVE"},
        description="Track name",
    )

    badness: bpy.props.FloatProperty(  # type: ignore
        name="Badness",
        options={"SKIP_SAVE"},
        min=0,
        description="The worst badness score for any marker movement of this track",
    )

    frame: bpy.props.IntProperty(  # type: ignore
        name="Test Property",
        options={"SKIP_SAVE"},
        min=0,
        description="Frame number of the worst badness score",
    )


class TRACKING_UL_BadnessItem(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        # Experiments show that the item is of class BadnessItem
        track_name = item.track
        layout.label(text=track_name)

        # FIXME: How do we right align this label?
        badness = item.badness
        layout.label(text=f"{badness:.1f}")

        # FIXME: How do we right align this label?
        frame = item.frame
        layout.label(text=str(frame))


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

        bad_tracks_prop = context.object.bad_tracks  # type: ignore
        bad_tracks_prop.clear()
        for track_name, badness in sorted(
            badnesses.items(), key=lambda item: item[1].amount, reverse=True
        ):
            new_property = bad_tracks_prop.add()
            new_property.track = track_name
            new_property.badness = badness.amount
            new_property.frame = badness.frame

            # FIXME: Debug statement, consider removing
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

        col = layout.column()
        row = col.row()
        row.operator("tracking.find_bad_tracks")

        row = col.row()
        row.template_list(
            listtype_name="TRACKING_UL_BadnessItem",
            list_id="",
            dataptr=context.object,
            propname="bad_tracks",
            active_dataptr=context.object,
            active_propname="active_bad_track",
            sort_lock=True,
        )


classes = (
    OP_Tracking_find_bad_tracks,
    TRACKING_PT_FindBadTracksPanel,
    TRACKING_UL_BadnessItem,
    BadnessItem,
)


def on_switch_active_bad_track(
    self: bpy.types.IntProperty, context: bpy.types.Context
) -> None:
    active_bad_track_index: int = context.object.active_bad_track  # type: ignore

    # Get the list entry from this index
    bad_tracks_collection = context.object.bad_tracks  # type: ignore
    badness_item: BadnessItem = bad_tracks_collection[active_bad_track_index]

    spaces = cast(bpy.types.AreaSpaces, context.area.spaces)
    active = cast(bpy.types.SpaceClipEditor, spaces.active)
    clip = active.clip

    # Get ourselves a reference to the bad track object
    all_tracks_collection = cast(bpy.types.bpy_prop_collection, clip.tracking.tracks)
    bad_track_index = all_tracks_collection.find(badness_item.track)
    bad_track = all_tracks_collection.values()[bad_track_index]

    # FIXME: Select only this track in the Tracking Dopesheet editor

    # Select only the clicked track in the Tracking Clip editor
    bpy.ops.clip.select_all(action="DESELECT")
    all_tracks_list = cast(List[MovieTrackingTrack], clip.tracking.tracks)
    for track in all_tracks_list:
        if track.name == badness_item.track:
            track.select = True

    # Skip to the worst frame
    #
    # NOTE: With Blender 2.93.1 the ordering here seems to matter. If you
    # frame_set() before change_frame() the clip view doesn't update properly.
    bpy.ops.clip.change_frame(badness_item.frame)
    context.scene.frame_set(badness_item.frame)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Ref: https://docs.blender.org/api/current/bpy.props.html#bpy.props.CollectionProperty
    #
    # Options and overrides are documented here:
    # https://github.com/dfelinto/blender/blob/master/source/blender/python/intern/bpy_props.c
    #
    # FIXME: Can we do "bpy.types.MovieTracking.bad_tracks =" here instead?
    bpy.types.Object.bad_tracks = bpy.props.CollectionProperty(
        type=BadnessItem,
        name="Bad Tracks",
        description="List of tracks sorted by badness score",
        options={"SKIP_SAVE"},
    )

    # FIXME: I don't care about selection right now, figure out what we really want here.
    bpy.types.Object.active_bad_track = bpy.props.IntProperty(
        name="Active Bad Track",
        description="Index of the currently active bad track",
        default=0,
        options={"SKIP_SAVE"},
        update=on_switch_active_bad_track,
    )


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    # Clear properties.
    del bpy.types.Object.bad_tracks


if __name__ == "__main__":
    register()
