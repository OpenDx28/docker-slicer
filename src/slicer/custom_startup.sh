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

rm -rf /home/kasm-user/Downloads
rm -rf /home/kasm-user/Uploads
rm -rf /home/kasm-user/Videos
rm -rf /home/kasm-user/Pictures
rm -rf /home/kasm-user/Music
rm -rf /home/kasm-user/Desktop
rm -rf /home/kasm-user/Public
rm -rf /home/kasm-user/Templates

touch /home/kasm-user/STORE_FILES_INSIDE_DOCUMENTS_DIR

cd /opt/easydav
python2 /opt/easydav/webdav.py &
cd ~

startup
