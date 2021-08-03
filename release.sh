#!/bin/bash

# https://sipb.mit.edu/doc/safe-shell/
set -euf -o pipefail

echo "Please decide on a new version number in 1.2.3 format"
read -r -p "Press RETURN > "

echo "Please make an annotated tag with git tag --annotate VERSION"
read -r -p "Press RETURN > "

echo "Please: cp __init__.py find_bad_tracks-VERSION.py"
read -r -p "Press RETURN > "

echo "Please update the version number in find_bad_tracks-VERSION.py"
read -r -p "Press RETURN > "

echo "Please: git push --tags"
read -r -p "Press RETURN > "

echo "Please upload find_bad_tracks-VERSION.py to the Github release page"
read -r -p "Press RETURN > "
