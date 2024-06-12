from typing import cast, List

from bpy.types import MovieClip, MovieTracking, MovieTrackingTrack, MovieTrackingTracks

from find_bad_motion_tracks.find_bad_tracks import (
    find_bad_tracks,
    BadnessCalculator,
    TrackWithFloat,
)


def make_clip() -> MovieClip:
    tracks: List[MovieTrackingTrack] = []

    clip = MovieClip()
    clip.frame_start = 0
    clip.frame_duration = 10
    clip.tracking = MovieTracking()
    clip.tracking.tracks = cast(MovieTrackingTracks, tracks)
    return clip


def test_find_bad_tracks_no_tracks() -> None:
    test_clip = make_clip()
    find_bad_tracks(test_clip)


def test_compute_badness_score() -> None:
    movingRight = TrackWithFloat(MovieTrackingTrack(), 10.0, 1)
    movingLeft = TrackWithFloat(MovieTrackingTrack(), -10.0, 1)

    movements: List[TrackWithFloat] = [
        movingRight,
        movingRight,
        movingRight,
        movingLeft,
    ]

    badness_calculator = BadnessCalculator(movements)

    leftScore = badness_calculator.compute_badness_score(movingLeft)
    rightScore = badness_calculator.compute_badness_score(movingRight)

    assert leftScore > rightScore
    assert leftScore > 0
