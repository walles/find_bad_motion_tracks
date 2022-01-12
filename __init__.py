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
import time
import operator
import statistics

from typing import Iterable, cast, List, Dict, Set, Tuple
from dataclasses import dataclass

from bpy.types import MovieClip, MovieTrackingMarkers, MovieTrackingTrack
from bpy.types import UILayout, Context, AnyType

bl_info = {
    "name": "Find Bad Tracks",
    "author": "Johan Walles",
    "description": "Highlight motion tracks that move in suspicious directions",
    "blender": (2, 93, 1),
    "version": (0, 0, 1),
    "location": "Clip Editor > Tools > Track > Find Bad Tracks",
    "warning": "",
    "doc_url": "https://github.com/walles/find_bad_motion_tracks#usage-instructions",
    "tracker_url": "https://github.com/walles/find_bad_motion_tracks/issues",
    "category": "Video Tools",
}

FIND_BAD_TRACKS = "Find Bad Tracks"

# If two points are further apart than this many percent of the image dimensions
# they are not dups (at least not in this frame).
DUP_MAXDIST_PERCENT = 1.0


@dataclass
class TrackWithFloat:
    track: MovieTrackingTrack
    number: float
    blame_frame: int


@dataclass
class Badness:
    amount: float
    frame: int


@dataclass
class Duplicate:
    track1_name: str
    track2_name: str
    frame: int


class BadnessItem(bpy.types.PropertyGroup):
    # FIXME: How do we make all of these read-only in the UI?

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
        name="Frame number",
        options={"SKIP_SAVE"},
        min=0,
        description="Frame number of the worst badness score",
    )


class DuplicateItem(bpy.types.PropertyGroup):
    # FIXME: How do we make all of these read-only in the UI?

    track1_name: bpy.props.StringProperty(  # type: ignore
        name="Tracks",
        options={"SKIP_SAVE"},
        description="Overlapping track name 1",
    )

    track2_name: bpy.props.StringProperty(  # type: ignore
        name="Tracks",
        options={"SKIP_SAVE"},
        description="Overlapping track name 2",
    )

    frame: bpy.props.IntProperty(  # type: ignore
        name="Frame number",
        options={"SKIP_SAVE"},
        min=0,
        description="Frame number of the first overlap",
    )


class TRACKING_UL_BadnessItem(bpy.types.UIList):
    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data: AnyType,
        item: AnyType,
        icon: int,
        active_data: AnyType,
        active_property: str,
        index: int = 0,
        flt_flag: int = 0,
    ):
        # Experiments show that the item is of class BadnessItem
        badnessItem = cast(BadnessItem, item)

        track_name = badnessItem.track
        layout.label(text=track_name)

        # FIXME: How do we right align this label?
        badness = badnessItem.badness
        layout.label(text=f"{badness:.1f}")

        # FIXME: Drop this, the UI is really narrow and clicking the line will
        # go to the bad frame anyway
        frame = badnessItem.frame
        layout.label(text=str(frame))


class TRACKING_UL_DuplicateItem(bpy.types.UIList):
    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data: AnyType,
        item: AnyType,
        icon: int,
        active_data: AnyType,
        active_property: str,
        index: int = 0,
        flt_flag: int = 0,
    ):
        duplicateItem = cast(DuplicateItem, item)
        layout.label(text=f"{duplicateItem.track1_name} & {duplicateItem.track2_name}")


class BadnessCalculator:
    def __init__(self, movements: List[TrackWithFloat]) -> None:
        # Take the median of all numbers.
        #
        # FIXME: Should we give higher weights to locked tracks? Since a human
        # has likely locked them because those tracks are known good?
        median = statistics.median(map(lambda movement: movement.number, movements))

        # For a 10 item list, this will be 8
        percentile_count = (len(movements) * 4) // 5
        assert 0 < percentile_count < len(movements)

        # For a 10 item list, with indices 0-9, this will be 7, skipping the two
        # last ones.
        percentile_index = percentile_count - 1

        distance = sorted(
            map(lambda movement: abs(movement.number - median), movements)
        )[percentile_index]

        self.median = median
        self.distance = distance

    def compute_badness_score(self, movement: TrackWithFloat) -> float:
        # Figure out how much this track moved compared to the median and the
        # movement wiggle room.
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


def get_active_clip(context: bpy.types.Context):
    spaces = cast(bpy.types.AreaSpaces, context.area.spaces)
    active = cast(bpy.types.SpaceClipEditor, spaces.active)
    return active.clip


def find_bad_tracks(clip: MovieClip) -> Dict[str, Badness]:
    # For each clip frame except the first...
    first_frame_index = clip.frame_start
    last_frame_index = clip.frame_start + clip.frame_duration - 1

    # Map track names to badness scores
    badnesses: Dict[str, Badness] = {}

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

        update_badnesses(badnesses, dx_list)
        update_badnesses(badnesses, dy_list)
        update_badnesses(badnesses, ddx_list)
        update_badnesses(badnesses, ddy_list)

    return badnesses


def find_duplicate_tracks(clip: MovieClip) -> Iterable[Duplicate]:

    dup_maxdist_fraction = DUP_MAXDIST_PERCENT / 100.0
    dup_maxdist2 = dup_maxdist_fraction * dup_maxdist_fraction

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
                if track1_name == track2_name:
                    continue

                if track1_name > track2_name:
                    # Require alphabetic order to avoid duplicates
                    continue

                dx = x2 - x1
                dy = y2 - y1
                dist2 = dx * dx + dy * dy
                if dist2 > dup_maxdist2:
                    continue

                if (track1_name, track2_name) in dups:
                    continue

                dup = Duplicate(track1_name, track2_name, frame_index)
                dups[(track1_name, track2_name)] = dup

    return dups.values()


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
        """
        If this method return False, our UI will be disabled.
        """
        # FIXME: Without at least three tracks we should return False here
        if context.edit_movieclip is None:
            return False
        return get_active_clip(context) is not None

    def execute(self, context: bpy.types.Context):
        clip = get_active_clip(context)

        t0 = time.time()

        badnesses = find_bad_tracks(clip)

        bad_tracks_prop = context.edit_movieclip.bad_tracks  # type: ignore
        bad_tracks_prop.clear()
        for track_name, badness in sorted(
            badnesses.items(), key=lambda item: item[1].amount, reverse=True
        ):
            new_property = bad_tracks_prop.add()
            new_property.track = track_name
            new_property.badness = badness.amount
            new_property.frame = badness.frame

        t1 = time.time()
        print(f"Finding bad tracks took {t1 - t0:.2f}s")

        t0 = time.time()

        dups = find_duplicate_tracks(clip)

        duplicate_tracks_prop = context.edit_movieclip.duplicate_tracks  # type: ignore
        duplicate_tracks_prop.clear()
        for dup in sorted(dups, key=operator.attrgetter("track1_name", "track2_name")):
            new_property = duplicate_tracks_prop.add()
            new_property.track1_name = dup.track1_name
            new_property.track2_name = dup.track2_name
            new_property.frame = dup.frame

        t1 = time.time()
        print(f"Finding duplicate tracks took {t1 - t0:.2f}s")

        return {"FINISHED"}


class TRACKING_PT_FindBadTracksPanel(bpy.types.Panel):
    bl_label = FIND_BAD_TRACKS
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Track"

    @classmethod
    def poll(cls, context):
        """
        If this method returns False our UI will not be visible.
        """
        # Fix for https://github.com/walles/find_bad_motion_tracks/issues/2
        return context.edit_movieclip is not None

    def draw(self, context):
        layout = self.layout

        # Draw the button
        col = layout.column()
        row = col.row()
        row.operator("tracking.find_bad_tracks")

        # Draw the bad-tracks list
        box = col.box()
        box.row().label(text="Bad Tracks")
        box.row().template_list(
            listtype_name="TRACKING_UL_BadnessItem",
            list_id="",
            dataptr=context.edit_movieclip,
            propname="bad_tracks",
            active_dataptr=context.edit_movieclip,
            active_propname="active_bad_track",
            sort_lock=True,
        )

        # Draw a duplicate-tracks list
        box = col.box()
        box.row().label(text="Duplicate Tracks")
        box.row().template_list(
            listtype_name="TRACKING_UL_DuplicateItem",
            list_id="",
            dataptr=context.edit_movieclip,
            propname="duplicate_tracks",
            active_dataptr=context.edit_movieclip,
            active_propname="active_duplicate_tracks",
            sort_lock=True,
        )


classes = (
    OP_Tracking_find_bad_tracks,
    TRACKING_PT_FindBadTracksPanel,
    TRACKING_UL_BadnessItem,
    TRACKING_UL_DuplicateItem,
    BadnessItem,
    DuplicateItem,
)


def on_switch_active_bad_track(
    self: bpy.types.IntProperty, context: bpy.types.Context
) -> None:
    if context.edit_movieclip is None:  # type: ignore
        return

    active_bad_track_index: int = context.edit_movieclip.active_bad_track  # type: ignore

    # Get the list entry from this index
    bad_tracks_collection = context.edit_movieclip.bad_tracks  # type: ignore
    badness_item: BadnessItem = bad_tracks_collection[active_bad_track_index]

    clip = get_active_clip(context)

    # Get ourselves a reference to the bad track object
    all_tracks_collection = cast(bpy.types.bpy_prop_collection, clip.tracking.tracks)
    bad_track_index = all_tracks_collection.find(badness_item.track)
    bad_track = all_tracks_collection.values()[bad_track_index]

    # FIXME: Select only this track in the Tracking Dopesheet editor
    # Asked here: https://blender.chat/channel/python?msg=6Zx3Nk6NKZMsmkxPy

    # Highlight this track on the right of the Tracking Clip editor
    movie_tracking_tracks = cast(bpy.types.MovieTrackingTracks, clip.tracking.tracks)
    movie_tracking_tracks.active = bad_track

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


def on_switch_active_duplicate_tracks(
    self: bpy.types.IntProperty, context: bpy.types.Context
) -> None:
    if context.edit_movieclip is None:  # type: ignore
        return

    active_duplicate_tracks_index: int = context.edit_movieclip.active_duplicate_tracks  # type: ignore

    # Get the list entry from this index
    duplicate_tracks_collection = context.edit_movieclip.duplicate_tracks  # type: ignore
    dup_item: DuplicateItem = duplicate_tracks_collection[active_duplicate_tracks_index]

    clip = get_active_clip(context)

    # Get ourselves a reference to the duplicate track objects
    all_tracks_collection = cast(bpy.types.bpy_prop_collection, clip.tracking.tracks)
    dup_track1_index = all_tracks_collection.find(dup_item.track1_name)
    dup_track1 = all_tracks_collection.values()[dup_track1_index]
    dup_track2_index = all_tracks_collection.find(dup_item.track2_name)
    dup_track2 = all_tracks_collection.values()[dup_track2_index]

    # FIXME: Select only this track in the Tracking Dopesheet editor
    # Asked here: https://blender.chat/channel/python?msg=6Zx3Nk6NKZMsmkxPy

    # Highlight one of the tracks on the right of the Tracking Clip editor
    movie_tracking_tracks = cast(bpy.types.MovieTrackingTracks, clip.tracking.tracks)
    movie_tracking_tracks.active = dup_track1

    # Select only the duplicate tracks in the Tracking Clip editor
    bpy.ops.clip.select_all(action="DESELECT")
    all_tracks_list = cast(List[MovieTrackingTrack], clip.tracking.tracks)
    for track in all_tracks_list:
        if track.name in (dup_item.track1_name, dup_item.track2_name):
            track.select = True

    # Skip to the first overlapping frame
    #
    # NOTE: With Blender 2.93.1 the ordering here seems to matter. If you
    # frame_set() before change_frame() the clip view doesn't update properly.
    bpy.ops.clip.change_frame(dup_item.frame)
    context.scene.frame_set(dup_item.frame)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Ref: https://docs.blender.org/api/current/bpy.props.html#bpy.props.CollectionProperty
    #
    # Options and overrides are documented here:
    # https://github.com/dfelinto/blender/blob/master/source/blender/python/intern/bpy_props.c
    bpy.types.MovieClip.bad_tracks = bpy.props.CollectionProperty(
        type=BadnessItem,
        name="Bad Tracks",
        description="List of tracks sorted by badness score",
        options={"SKIP_SAVE"},
    )

    bpy.types.MovieClip.active_bad_track = bpy.props.IntProperty(
        name="Active Bad Track",
        description="Index of the currently active bad track",
        default=0,
        options={"SKIP_SAVE"},
        update=on_switch_active_bad_track,
    )

    bpy.types.MovieClip.duplicate_tracks = bpy.props.CollectionProperty(
        type=DuplicateItem,
        name="Duplicate Tracks",
        description="List of duplicate tracks",
        options={"SKIP_SAVE"},
    )

    bpy.types.MovieClip.active_duplicate_tracks = bpy.props.IntProperty(
        name="Active Duplicate Tracks Pair",
        description="Index of the currently active duplicate tracks pair",
        default=0,
        options={"SKIP_SAVE"},
        update=on_switch_active_duplicate_tracks,
    )


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    # Clear properties.
    del bpy.types.MovieClip.bad_tracks
    del bpy.types.MovieClip.active_bad_track
    del bpy.types.MovieClip.duplicate_tracks
    del bpy.types.MovieClip.active_duplicate_tracks


if __name__ == "__main__":
    register()
