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

#
# This file contains all Blender UI related code.
#

import bpy
import time
import operator

from typing import cast, List, Optional, Tuple

from bpy.types import (
    AnyType,
    bpy_prop_collection,
    Context,
    MovieTrackingMarker,
    MovieTrackingTrack,
    UILayout,
)

from .find_bad_tracks import find_bad_tracks
from .find_duplicate_tracks import find_duplicate_tracks

FIND_BAD_TRACKS = "Find Bad Tracks"


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
        context: Context | None,
        layout: UILayout,
        data: AnyType | None,
        item: AnyType | None,
        icon: int | None,
        active_data: AnyType,
        active_property: str,
        index: int | None = 0,
        flt_flag: int | None = 0,
    ):
        if item is None:
            return

        # Experiments show that the item is of class BadnessItem
        badnessItem = cast(BadnessItem, item)

        track_name = badnessItem.track
        layout.label(text=track_name)

        # FIXME: How do we right align this label?
        badness = badnessItem.badness
        layout.label(text=f"{badness:.1f}")


class TRACKING_UL_DuplicateItem(bpy.types.UIList):
    def draw_item(
        self,
        context: Context | None,
        layout: UILayout,
        data: AnyType | None,
        item: AnyType | None,
        icon: int | None,
        active_data: AnyType,
        active_property: str,
        index: int | None = 0,
        flt_flag: int | None = 0,
    ):
        if item is None:
            return

        duplicateItem = cast(DuplicateItem, item)
        layout.label(text=f"{duplicateItem.track1_name} & {duplicateItem.track2_name}")


def get_active_clip(context: bpy.types.Context):
    spaces = cast(bpy.types.AreaSpaces, context.area.spaces)
    active = cast(bpy.types.SpaceClipEditor, spaces.active)
    return active.clip


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

        for dup in sorted(dups, key=operator.attrgetter("maxdist2"), reverse=True):
            new_property = duplicate_tracks_prop.add()
            new_property.track1_name = dup.track1_name
            new_property.track2_name = dup.track2_name
            new_property.frame = dup.most_interesting_frame()

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
    _: bpy.types.IntProperty, context: bpy.types.Context
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

    # Select only the clicked track and no others in the Tracking Clip editor
    all_tracks_list = cast(List[MovieTrackingTrack], clip.tracking.tracks)
    for track in all_tracks_list:
        track.select = track.name == badness_item.track

    # Skip to the worst frame
    #
    # NOTE: With Blender 2.93.1 the ordering here seems to matter. If you
    # frame_set() before change_frame() the clip view doesn't update properly.
    bpy.ops.clip.change_frame(badness_item.frame)
    context.scene.frame_set(badness_item.frame)


def get_first_last_frames(track: MovieTrackingTrack) -> Tuple[int, int]:
    markers_collection = cast(bpy_prop_collection, track.markers)
    first: Optional[int] = None
    last: Optional[int] = None
    for marker in markers_collection.values():
        marker = cast(MovieTrackingMarker, marker)
        frame = marker.frame
        if first is None or frame < first:
            first = frame
        if last is None or frame > last:
            last = frame

    assert first is not None and last is not None
    return (first, last)


def get_front_track(
    t1: MovieTrackingTrack, t2: MovieTrackingTrack
) -> MovieTrackingTrack:
    """Decide which track to put in front of the other"""
    t1_start, t1_end = get_first_last_frames(t1)
    t2_start, t2_end = get_first_last_frames(t2)

    len_t1 = t1_end - t1_start
    len_t2 = t2_end - t2_start
    if len_t2 < len_t1:
        return t2

    # t1 is shorter or same length
    return t1


def on_switch_active_duplicate_tracks(
    _: bpy.types.IntProperty, context: bpy.types.Context
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
    dup_track1: MovieTrackingTrack = all_tracks_collection.values()[dup_track1_index]
    dup_track2_index = all_tracks_collection.find(dup_item.track2_name)
    dup_track2: MovieTrackingTrack = all_tracks_collection.values()[dup_track2_index]

    # FIXME: Select only this track in the Tracking Dopesheet editor
    # Asked here: https://blender.chat/channel/python?msg=6Zx3Nk6NKZMsmkxPy

    # Highlight one of the tracks on the right of the Tracking Clip editor
    movie_tracking_tracks = cast(bpy.types.MovieTrackingTracks, clip.tracking.tracks)
    movie_tracking_tracks.active = get_front_track(dup_track1, dup_track2)

    # Select only the duplicate tracks in the Tracking Clip editor and no others
    all_tracks_list = cast(List[MovieTrackingTrack], clip.tracking.tracks)
    for track in all_tracks_list:
        track.select = track.name in (dup_item.track1_name, dup_item.track2_name)

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
