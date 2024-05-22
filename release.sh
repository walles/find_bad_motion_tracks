#!/bin/bash

# https://sipb.mit.edu/doc/safe-shell/
set -euf -o pipefail

FIXME: This script should create a .zip file
FIXME: This script should bump the version numbers in both the manifest file and the .py file before packaging
FIXME: This script should prompt for uploading to https://extensions.blender.org

echo "## Old version numbers:"
git tag | cat
echo
echo "Please enter the new version number in 1.2.3 format"
read -r -p "> " VERSION

echo
echo "The tag description will be on the releases page on Github, write something nice!"
git tag --annotate "$VERSION"

# If we name it with 1.2.3 at the end Blender fails to load it, so the .py file
# name version number must be underscore separated.
UNDERSCORE_VERSION=$(echo "$VERSION" | tr . _)
COMMAS_VERSION="${UNDERSCORE_VERSION//_/, }"
sed "s/    \"version\": .*/    \"version\": ($COMMAS_VERSION),/" <"__init__.py" >"find_bad_tracks-${UNDERSCORE_VERSION}.py"

git push --tags

echo "Please upload find_bad_tracks-${UNDERSCORE_VERSION}.py at https://github.com/walles/find_bad_motion_tracks/releases/tag/$VERSION"
read -r -p "Press RETURN when done > "
