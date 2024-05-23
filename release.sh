#!/bin/bash

# https://sipb.mit.edu/doc/safe-shell/
set -eu -o pipefail
shopt -s failglob

echo "## Old version numbers:"
git tag | cat
echo
echo "Please enter the new version number in 1.2.3 format"
read -r -p "> " VERSION

WORKDIR=$(mktemp -d)
trap 'rm -rf ${WORKDIR}' EXIT

# Create a find-bad-tracks-1_2_3.zip file containing files with the new version
# number in them. This is what should be uploaded to Blender's extension site.
UNDERSCORE_VERSION=$(echo "$VERSION" | tr . _)
COMMAS_VERSION="${UNDERSCORE_VERSION//_/, }"
ZIPNAME="${PWD}/find-bad-motion-tracks-${UNDERSCORE_VERSION}.zip"
mkdir "${WORKDIR}/find_bad_motion_tracks"
sed "s/    \"version\": .*/    \"version\": ($COMMAS_VERSION),/" <"__init__.py" >"${WORKDIR}/find_bad_motion_tracks/__init__.py"
sed "s/^version = .*/version = \"${VERSION}\"/" <blender_manifest.toml >"${WORKDIR}/find_bad_motion_tracks/blender_manifest.toml"
pushd "${WORKDIR}" >/dev/null
zip -r "${ZIPNAME}" "find_bad_motion_tracks" >/dev/null
popd >/dev/null

echo
echo "The tag description will be on the releases page on Github, write something nice!"
git tag --annotate "$VERSION"

git push --tags

echo "Please upload ${ZIPNAME} at https://github.com/walles/find_bad_motion_tracks/releases/tag/$VERSION"
read -r -p "Press RETURN when done > "

echo "Please upload ${ZIPNAME} at https://extensions.blender.org"
read -r -p "Press RETURN when done > "
