#!/bin/bash

# https://sipb.mit.edu/doc/safe-shell/
set -euf -o pipefail

echo "## Old version numbers:"
git tag | cat
echo
echo "Please enter the new version number in 1.2.3 format"
read -r -p "> " VERSION

echo
echo "The tag description will be on the releases page on Github, write something nice!"
git tag --annotate "$VERSION"

RELEASE_DIR="releases/$VERSION"
mkdir "$RELEASE_DIR"

UNDERSCORE_VERSION=$(echo "$VERSION" | tr . _)
COMMAS_VERSION="${UNDERSCORE_VERSION//_/, }"
sed "s/    \"version\": .*/    \"version\": ($COMMAS_VERSION),/" <"__init__.py" >"$RELEASE_DIR/find_bad_tracks.py"

git push --tags

echo "Please upload $RELEASE_DIR/find_bad_tracks.py at https://github.com/walles/find_bad_motion_tracks/releases/tag/$VERSION"
read -r -p "Press RETURN when done > "
