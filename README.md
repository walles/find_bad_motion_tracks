# Find Bad Motion Tracks

This is a [Blender](https://blender.org)
[addon](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html)
for finding bad [motion tracking
tracks](https://docs.blender.org/manual/en/latest/movie_clip/tracking/clip/editing/track.html).

The way it works is that it highlights tracks that move differently from the
others.

Basically, if all tracks move to the right, except one that moves to the left,
then the single track moving to the left is likely wrong and should be evaluated
by a human.

## Installation Instructions

FIXME: None yet, half of the UI is still in the Blender console, that needs to
be fixed before I feel comfortable trying to get anybody but me to use this.

## Usage Instructions

1. Make sure [you can see the Blender
   console](https://blender.stackexchange.com/a/119523/20467) (FIXME: Move UI
   into Blender itself)
2. Make sure the addon is enabled, I'm using the VS Code Blender extension for
   this right now (FIXME: This is sucky advise)
3. Do some motion tracking, collect some tracks
4. In the Motion Tracking workspace, Movie Clip Editor on the middle left of
   your screen, select the Track tab, expand "Find Bad Tracks" (you may have to
   scroll down to see this section) and press the "Find Bad Tracks" button
5. **A list of all tracks with badness scores will now be printed to the Blender
   console**. Go fix them!

## Development

I have developed this with:

- [Visual Studio Code](https://code.visualstudio.com/) with its [Blender Development
  extension](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development)
- The [Fake Blender Python API module collection](https://github.com/nutti/fake-bpy-module) in a virtualenv
- Blender 2.93.1
