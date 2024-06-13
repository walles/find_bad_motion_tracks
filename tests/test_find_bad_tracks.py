from typing import cast, List

from bpy.types import (
    MovieClip,
    MovieTracking,
    MovieTrackingTrack,
    MovieTrackingTracks,
    MovieTrackingMarker,
)

from find_bad_motion_tracks.find_bad_tracks import (
    find_bad_tracks,
    shape_change_amount,
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


def test_compute_shape_change_amount():
    previous_marker = MovieTrackingMarker()
    previous_marker.pattern_corners = [[0, 0], [0, 1], [1, 1], [1, 0]]

    assert shape_change_amount(previous_marker, previous_marker) == 0.0

    marker = MovieTrackingMarker()
    marker.pattern_corners = [[0, 0], [0, 1], [1, 1], [1, 5]]

    # The exact value here doesn't matter, but it needs to be noticeably bigger
    # than with no marker change
    assert shape_change_amount(previous_marker, marker) == 5.0
