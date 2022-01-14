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

1. Go to the [latest release download page](https://github.com/walles/find_bad_motion_tracks/releases/latest)
1. Download the `find_bad_tracks-A_B_C.py` file
1. In Blender, open Preferences (under the <kbd>Edit</kbd> menu)
1. Click <kbd>Add-ons</kbd>
1. Click the <kbd>Install...</kbd> button
1. Find the file you just downloaded and click <kbd>Install Add-on</kbd>
1. Check the box next to <kbd>Video Tools: Find Bad Tracks</kbd>

## Usage Instructions

1. Follow the Installation Instructions `^` for how to install and enable this addon
1. Do some motion tracking, collect some tracks
1. In the Motion Tracking workspace, Movie Clip Editor on the middle left of
   your screen, select the <kbd>Track</kbd> tab, expand <kbd>Find Bad Tracks</kbd> (you may have to
   scroll down to see this section) and press the <kbd>Find Bad Tracks</kbd> button
1. A list of tracks will now be displayed just below that button, with the worst
   frame number for each track and its badness score at that point.
1. Clicking a track in the list will select that track in the clip editor and
   take you to the worst frame. Stepping a frame left will show how the track
   skips / slides.

![Example usage](example.png 'Example usage')

# Comparison to Built-in Functionality

Find Bad Tracks is similar to the built-in [Filter
Tracks](https://docs.blender.org/manual/en/latest/movie_clip/tracking/clip/editing/track.html#filter-tracks)
functionality ([source](https://github.com/blender/blender/blob/04c75c5ce7699a1502a7c2212d4aa57166465514/release/scripts/startup/bl_operators/clip.py#L141-L215)).

<!-- Table generated by https://www.tablesgenerator.com/markdown_tables -->

|                        | Find Bad Tracks                                                                                                                          | Filter Tracks                                                                                                                   |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Finding the midpoint   | :green_heart: Uses median, resilient to outliers                                                                                         | :broken_heart: Uses average, sensitive to outliers                                                                              |
| Threshold              | :green_heart: N/A, calculates a badness value based on the 80th percentile of track movements, works on both fast and slow moving frames | :broken_heart: 5 pixels, too sensitive on fast moving frames, too lenient on slow moving frames                                 |
| Uses derivative        | :green_heart:                                                                                                                            | :green_heart:                                                                                                                   |
| Uses 2nd derivative    | :green_heart:                                                                                                                            | :broken_heart: No, which means the Filtering will miss tracks which suddenly move in a new direction                            |
| Presentation           | :green_heart: List tracks ranked by badness, lets user filter                                                                            | :broken_heart: Just selects all "bad" tracks, in my case that included lots of good tracks making the signal-to-noise ratio bad |
| Finds duplicate tracks | :green_heart:                                                                                                                            | :broken_heart:                                                                                                                  |

## Development

I have developed this with:

- [Visual Studio Code](https://code.visualstudio.com/) with its [Blender Development
  extension](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development)
- The [Fake Blender Python API module collection](https://github.com/nutti/fake-bpy-module) in a virtualenv
- Blender 2.93.1

## Making a New Release

1. Make sure the screenshot and description ^ are both up to date and in sync.
1. Run `release.sh` and follow instructions.

## TODO

- Add a `tox` Github action for PRs and pushes
- Fix the tracks list tooltips, the current ones make no sense: "Active Bad
  Track / Double click to rename."
- Profile and see what can easily be sped up
- Publish on Blender Market

### DONE

- Document a release process
- Make an initial release
- Document install instructions higher up in this document
- Ignore locked tracks, assuming they have been manually vetted by a human
- Announce on BlenderNation
- Fix user reported issues
- Add duplicate tracks detection
- Remove worst-frame column from the bad-tracks list.
- Properly deselect unrelated tracks when switching between duplicate track
  pairs in the UI
- Add a `tox.ini` with `mypy`, `pylint` and `black` code formatting. Black
  formats locally and verifies in CI.
