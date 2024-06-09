#!/bin/bash

# Create a find-bad-tracks-1_2_3.zip file containing files with the new version
# number in them. This is what should be uploaded to Blender's extension site.

# https://sipb.mit.edu/doc/safe-shell/
set -eu -o pipefail
shopt -s failglob

# Read version number parameter
if [ $# -ne 1 ]; then
    echo >&2 "Usage: $0 <version>"
    exit 1
fi
VERSION=$1

# Validate that the version is in 1.2.3 format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo >&2 "Version number must be in 1.2.3 format: $VERSION"
    exit 1
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf ${WORKDIR}' EXIT

# Create the zip file
UNDERSCORE_VERSION=$(echo "$VERSION" | tr . _)
ZIPNAME="${PWD}/find-bad-motion-tracks-${UNDERSCORE_VERSION}.zip"
cp -a find_bad_motion_tracks "${WORKDIR}/"
sed "s/^version = .*/version = \"${VERSION}\"/" <blender_manifest.toml >"${WORKDIR}/find_bad_motion_tracks/blender_manifest.toml"
pushd "${WORKDIR}" >/dev/null
zip -r "${ZIPNAME}" "find_bad_motion_tracks" >/dev/null
popd >/dev/null

echo "${ZIPNAME}"
