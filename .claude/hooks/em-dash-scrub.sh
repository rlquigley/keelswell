#!/usr/bin/env bash
# Em-dash scrub: the diff's added lines must contain zero U+2014 characters.
count=$(git diff | grep '^+' | grep -c $'\xe2\x80\x94')
if [ "${count:-0}" -ne 0 ]; then
  echo "em-dash-scrub: $count em-dash(es) introduced; replace with ' -- '" >&2
  exit 1
fi
exit 0
