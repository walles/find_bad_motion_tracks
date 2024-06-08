#!/bin/bash

# https://sipb.mit.edu/doc/safe-shell/
set -eu -o pipefail
shopt -s failglob

echo "## Old version numbers:"
git tag | cat
echo
echo "Please enter the new version number in 1.2.3 format"
read -r -p "> " VERSION

PACKAGED=$(./package-versioned-zip.sh "$VERSION")
echo Packaged into: "$PACKAGED"

echo
echo "The tag description will be on the releases page on Github, write something nice!"
git tag --annotate "$VERSION"

git push --tags

echo "Please upload ${PACKAGED} at https://github.com/walles/find_bad_motion_tracks/releases/tag/$VERSION"
read -r -p "Press RETURN when done > "

echo "Please upload ${PACKAGED} at https://extensions.blender.org"
read -r -p "Press RETURN when done > "
