from typing import cast, List, Tuple, Optional, Union, Any

from bpy.types import (
    MovieClip,
    MovieTracking,
    MovieTrackingTrack,
    MovieTrackingTracks,
    MovieTrackingMarkers,
    MovieTrackingMarker,
)

from find_bad_motion_tracks.find_bad_tracks import (
    find_bad_tracks,
    shape_change_amount,
    Badness,
    BadnessCalculator,
    TrackWithFloat,
)


class FakeMovieTrackingMarkers(MovieTrackingMarkers):
    def __init__(self, coordinates: List[Tuple[float, float]]) -> None:
        super().__init__()

        self.coordinates = coordinates

    def find_frame(
        self, frame: Optional[int], exact: Optional[Union[bool, Any]] = True
    ) -> "MovieTrackingMarker":
        marker = MovieTrackingMarker()
        if frame is None or frame < 0 or frame >= len(self.coordinates):
            marker.mute = True
            return marker

        marker.co = self.coordinates[frame]

        # Badness code expects markers to come with four corners. Corners are
        # relative to the marker position, so we give all markers the same
        # corners.
        marker.pattern_corners = [[-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0]]
        return marker


def make_clip() -> MovieClip:
    """
    Create a clip with two frames and four tracks, each track moving 10 to the right.

    Each track is a list of x-y coordinate tuples.

    Each x-y coordinate tuple represents the marker position at one frame.
    """
    movieTrackingTracks: List[MovieTrackingTrack] = []
    for i in range(4):
        movieTrackingTrack = MovieTrackingTrack()
        movieTrackingTrack.name = f"Track {i}"

        y = i * 10.0 + 10.0
        track = [(0.0 + y * 20.0, y), (10.0 + y * 20.0, y)]
        movieTrackingTrack.markers = FakeMovieTrackingMarkers(track)

        movieTrackingTracks.append(movieTrackingTrack)

    clip = MovieClip()
    clip.frame_start = 0
    clip.frame_duration = 2
    clip.tracking = MovieTracking()
    clip.tracking.tracks = cast(MovieTrackingTracks, movieTrackingTracks)
    return clip


def test_find_bad_tracks_all_good() -> None:
    assert find_bad_tracks(make_clip()) == {
        "Track 0": Badness(0.0, 1),
        "Track 1": Badness(0.0, 1),
        "Track 2": Badness(0.0, 1),
        "Track 3": Badness(0.0, 1),
    }


def test_find_bad_tracks_with_shape_change() -> None:
    clip = make_clip()

    # Originally [-1, -1]
    cast(FakeMovieTrackingMarkers, clip.tracking.tracks[0].markers).coordinates[0] = (
        -11.0,  # Originally -1.0, this value is 10 off
        -1.0,
    )

    assert find_bad_tracks(clip) == {
        "Track 0": Badness(1.0, 1),  # Badness gets normalized to 1.0
        "Track 1": Badness(0.0, 1),
        "Track 2": Badness(0.0, 1),
        "Track 3": Badness(0.0, 1),
    }

    # Originally [-1, -1]
    cast(FakeMovieTrackingMarkers, clip.tracking.tracks[0].markers).coordinates[0] = (
        -1.0,
        9.0,  # Originally -1.0, this value is 10 off
    )

    assert find_bad_tracks(clip) == {
        "Track 0": Badness(1.0, 1),  # Badness gets normalized to 1.0
        "Track 1": Badness(0.0, 1),
        "Track 2": Badness(0.0, 1),
        "Track 3": Badness(0.0, 1),
    }


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
