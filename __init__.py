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

bl_info = {
    "name": "Find Bad Motion Tracks",
    "author": "Johan Walles",
    "description": "",
    "blender": (2, 93, 1),
    "version": (0, 0, 1),
    # FIXME: Put this under Tracks
    "location": "Clip Editor > Tools > Solve > Find Bad Tracks",
    "warning": "",
    # FIXME: What should this be?
    "category": "Tools",
}


class OP_Tracking_reset_solution(bpy.types.Operator):
    """Reset track weight and solve camera motion"""

    bl_idname = "tracking.find_bad_tracks"
    bl_label = "Find bad motion tracks"

    @classmethod
    def poll(cls, context):
        # FIXME: Return true if we have any tracks, this method is a duplicate!
        return context.area.spaces.active.clip is not None

    def execute(self, context):
        print("Johan")
        return {"FINISHED"}


class FindBadTracksPanel(bpy.types.Panel):
    bl_label = "Find bad motion tracks"
    bl_space_type = "CLIP_EDITOR"  # FIXME: What should this be?
    bl_region_type = "TOOLS"  # FIXME: What should this be?
    bl_category = "Solve"  # FIXME: What should this be?

    @classmethod
    def poll(cls, context):
        # FIXME: Return true if we have any tracks, this method is a duplicate!
        return context.area.spaces.active.clip is not None

    def draw(self, context):
        # FIXME: Make sure this looks OK
        layout = self.layout
        box = layout.box()
        row = box.row(align=True)
        row.operator("tracking.find_bad_tracks")


def register():
    bpy.utils.register_module(__name__)


def unregister():
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
