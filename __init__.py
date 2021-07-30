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

from typing import cast

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


class OP_Tracking_find_bad_tracks(bpy.types.Operator):
    """
    FIXME: Long comment here, this text appears in the Blender UI.

    It shows up when hovering the button for this operation.
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
        for frame_index in range(first_frame_index + 1, last_frame_index):
            # FIXME: For each track...

            # FIXME: How much did this track move X and Y since the previous frame?

            # FIXME: Take the median of all movements between previous and this
            # frame, for X and Y independently.

            # FIXME: For each track, figure out how much this track moved compared
            # to the median, on X and Y independently.

            # FIXME: For each track, keep track of the largest difference vs the
            # median so far, for X and Y independently.
            pass

        # FIXME: Print all track names to the console, sorted by
        # max(xdifference, ydifference) for each track.
        print("Johan")
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
