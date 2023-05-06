#!/bin/bash
set -ex

ARCH=$(arch | sed 's/aarch64/arm64/g' | sed 's/x86_64/amd64/g')

# intall squid
SQUID_COMMIT='1149fc830c7edcb383eec390cce2beba16befde5'
if  $(grep -q Jammy /etc/os-release) || $(grep -q Kali /etc/os-release) ; then
  apt-get update
  apt-get install -y squid-openssl
  mkdir -p /usr/local/squid/sbin
  mkdir -p /usr/local/squid/var/logs/
  ln -s /usr/lib/squid/ /usr/local/squid/libexec
  ln -s /usr/sbin/squid /usr/local/squid/sbin/squid
elif [[ "${DISTRO}" != @(centos|oracle7|oracle8|oracle9|opensuse|fedora37|rockylinux9|rockylinux8|almalinux9|almalinux8|alpine) ]] ; then
  wget -qO- https://kasmweb-build-artifacts.s3.amazonaws.com/kasm-squid-builder/${SQUID_COMMIT}/output/kasm-squid-builder_${ARCH}.tar.gz | tar -xzf - -C /
fi

# update squid conf with user info
if [[ "${DISTRO}" == @(centos|oracle7|oracle8|oracle9|fedora37|almalinux8|almalinux9|rockylinux8|rockylinux9|alpine) ]]; then
  useradd --system --shell /usr/sbin/nologin --home-dir /bin proxy
elif [ "${DISTRO}" == "opensuse" ]; then
  useradd --system --shell /usr/sbin/nologin --home-dir /bin proxy
  groupadd -g 65511 proxy
  usermod -a -G proxy proxy
fi

mkdir /usr/local/squid/etc/ssl_cert -p
chown proxy:proxy /usr/local/squid/etc/ssl_cert -R
chmod 700 /usr/local/squid/etc/ssl_cert -R
cd /usr/local/squid/etc/ssl_cert

if [[ "${DISTRO}" == "fedora37" ]]; then
  dnf install -y openssl1.1 xkbcomp
  rm -f /etc/X11/xinit/xinitrc
elif [[ "${DISTRO}" == @(rockylinux9|oracle9|almalinux9) ]]; then
  dnf install -y compat-openssl11 xkbcomp
  rm -f /etc/X11/xinit/xinitrc
elif [[ "${DISTRO}" == @(centos|oracle7) ]]; then
  yum install -y openssl11-libs
elif [[ "${DISTRO}" == "alpine" ]]; then
  apk add --no-cache openssl1.1-compat
fi

/usr/local/squid/libexec/security_file_certgen -c -s /usr/local/squid/var/logs/ssl_db -M 4MB
chown proxy:proxy /usr/local/squid/var/logs/ssl_db -R

chown -R proxy:proxy /usr/local/squid -R

mkdir -p /etc/squid/

# Trick so we can auto re-direct blocked urls to a special page
cat >>/etc/squid/blocked.acl <<EOL
.access_denied
EOL
chown -R proxy:proxy /etc/squid/blocked.acl


if [[ "${DISTRO}" == @(centos|oracle7) ]]; then
  yum install -y memcached cyrus-sasl iproute
elif [[ "${DISTRO}" == @(oracle8|fedora37|oracle9|rockylinux9|rockylinux8|almalinux9|almalinux8) ]]; then
  dnf install -y memcached cyrus-sasl iproute
elif [ "${DISTRO}" == "opensuse" ]; then
  zypper install -yn memcached cyrus-sasl iproute2 libatomic1
elif [[ "${DISTRO}" == "alpine" ]]; then
  apk add --no-cache memcached cyrus-sasl iproute2 libatomic
else
  apt-get install -y memcached sasl2-bin iproute2
fi

# Enable SASL in the memchache config
echo "-S" >> /etc/memcached.conf

mkdir -p /etc/sasl2
cat >>/etc/sasl2/memcached.conf <<EOL
mech_list: plain
log_level: 5
sasldb_path: /etc/sasl2/memcached-sasldb2
EOL

KASM_SQUID_ADAPTER=https://kasmweb-build-artifacts.s3.amazonaws.com/kasm_squid_adapter/e46edd9bb45327359bc42f96cd2f299e23760904/kasm_squid_adapter_${ARCH}_develop.e46edd.tar.gz

wget -qO- ${KASM_SQUID_ADAPTER} | tar xz -C /etc/squid/
ls -la /etc/squid
chmod +x /etc/squid/kasm_squid_adapter

# FIXME - This likely should be moved somewhere else to be more explicit
# Install Cert utilities
if [[ "${DISTRO}" == @(centos|oracle7) ]]; then
  yum install -y nss-tools
elif [[ "${DISTRO}" == @(oracle8|fedora37|oracle9|rockylinux9|rockylinux8|almalinux9|almalinux8) ]]; then
  dnf install -y nss-tools
elif [ "${DISTRO}" == "opensuse" ]; then
  zypper install -yn mozilla-nss-tools
elif [ "${DISTRO}" == "alpine" ]; then
  apk add --no-cache nss-tools
else
  apt-get install -y libnss3-tools
fi

# Create an empty cert9.db. This will be used by applications like Chrome
mkdir -p $HOME/.pki/nssdb/
certutil -N -d sql:$HOME/.pki/nssdb/ --empty-password
chown 1000:1000 $HOME/.pki/nssdb/


cat >/usr/bin/filter_ready <<EOL
#!/usr/bin/env bash
if [ "\${http_proxy}" == "http://127.0.0.1:3128" ] ;
then
    while netstat -lnt | awk '\$4 ~ /:3128/ {exit 1}'; do sleep 1; done
    echo 'filter is ready'
else
    echo 'filter is not configured'
fi

EOL
chmod +x /usr/bin/filter_ready
