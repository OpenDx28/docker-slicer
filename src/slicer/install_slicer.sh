#!/usr/bin/env bash

set -ex

cd "$(dirname "$0")"

apt-get update
apt-get install -y libpulse-dev libnss3 libglu1-mesa
apt-get install -y --reinstall libxcb-xinerama0
apt-get clean

wget $SLICER_DOWNLOAD_URL -O slicer.tar.gz

mkdir /slicer
tar -xf slicer.tar.gz -C /slicer --strip-components 1

cat >/usr/bin/slicer <<EOF
#!/usr/bin/env bash
echo "Starting 3D Slicer with GPU Acceleration"
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia /slicer/Slicer
EOF
chmod +x /usr/bin/slicer

rm -rf /tmp/* /var/lib/apt/lists/* /var/tmp/*
