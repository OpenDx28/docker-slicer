#!/usr/bin/env bash

set -ex
START_COMMAND="slicer"
PGREP="Slicer"
export MAXIMIZE="true"
export MAXIMIZE_NAME="3D Slicer $SLICER_VERSION"
MAXIMIZE_SCRIPT=$STARTUPDIR/maximize_window.sh
DEFAULT_ARGS=""
ARGS=${APP_ARGS:-$DEFAULT_ARGS}

startup() {
    echo "Entering process startup loop"
    set +x
    while true; do
        if ! pgrep -x $PGREP >/dev/null; then
            /usr/bin/filter_ready
            /usr/bin/desktop_ready
            set +e
            bash ${MAXIMIZE_SCRIPT} &
            $START_COMMAND $ARGS
            set -e
        fi
        sleep 1
    done
    set -x

}

service apache2 start
startup
