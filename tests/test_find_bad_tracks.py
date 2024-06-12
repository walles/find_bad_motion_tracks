from typing import cast, List

from bpy.types import MovieClip, MovieTracking, MovieTrackingTrack, MovieTrackingTracks

from find_bad_motion_tracks.find_bad_tracks import find_bad_tracks


def make_clip() -> MovieClip:
    tracks: List[MovieTrackingTrack] = []

    clip = MovieClip()
    clip.frame_start = 0
    clip.frame_duration = 10
    clip.tracking = MovieTracking()
    clip.tracking.tracks = cast(MovieTrackingTracks, tracks)
    return clip


def test_find_bad_tracks_no_tracks():
    test_clip = make_clip()
    find_bad_tracks(test_clip)
