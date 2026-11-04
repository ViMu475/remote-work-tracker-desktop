#!/bin/sh
# Start script of the installed packages: keeps the state file in the user's own data folder,
# because the program folder (/opt/...) is not writable for normal users.
data="${XDG_DATA_HOME:-$HOME/.local/share}/remote-work-tracker"
mkdir -p "$data"
export RW_DATA_FILE="${RW_DATA_FILE:-$data/tracker_state.json}"
exec /opt/remote-work-tracker/RemoteWorkTracker "$@"
