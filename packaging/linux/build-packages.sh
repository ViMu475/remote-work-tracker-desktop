#!/bin/bash
# Builds .deb and .rpm from the finished Linux program (dist/RemoteWorkTracker).
#
#   packaging/linux/build-packages.sh <program> <version> <output folder>
#
# Needs: dpkg-deb + fakeroot (.deb), rpmbuild (.rpm).
# A missing tool skips its format with a message. Nothing is installed or signed here.
# The packages need a glibc at least as new as the one of the build machine (checked below).
set -euo pipefail

PROGRAM="$(readlink -f "$1")"
VERSION="$2"
mkdir -p "$3"
OUT="$(readlink -f "$3")"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

[ -x "$PROGRAM" ] || { echo "Program not found or not executable: $PROGRAM"; exit 1; }
MAINTAINER="ViMu475 <ViMu475@users.noreply.github.com>"
# PyInstaller bundles libraries of the build machine, so the glibc of THIS machine is the safe minimum
# (the program's own header only shows the old requirement of the boot loader).
GLIBC="$(getconf GNU_LIBC_VERSION | awk '{print $2}')"
echo "Packages require glibc $GLIBC or newer (glibc of the build machine)"

install_tree() {  # $1 = root folder of the installed files
    install -D -m 755 "$PROGRAM" "$1/opt/remote-work-tracker/RemoteWorkTracker"
    install -D -m 755 "$HERE/remote-work-tracker.sh" "$1/usr/bin/remote-work-tracker"
    install -D -m 644 "$HERE/remote-work-tracker.desktop" "$1/usr/share/applications/remote-work-tracker.desktop"
    install -D -m 644 "$ROOT/static/icons/icon.svg" "$1/usr/share/icons/hicolor/scalable/apps/remote-work-tracker.svg"
    install -D -m 644 "$ROOT/LICENSE" "$1/usr/share/doc/remote-work-tracker/copyright"
}

# ---- .deb ---------------------------------------------------------------------------------
if command -v dpkg-deb >/dev/null && command -v fakeroot >/dev/null; then
    T="$WORK/deb"; install_tree "$T"
    mkdir -p "$T/DEBIAN"
    SIZE="$(du -sk "$T" | cut -f1)"
    cat > "$T/DEBIAN/control" <<EOF
Package: remote-work-tracker
Version: $VERSION
Section: office
Priority: optional
Architecture: amd64
Depends: libc6 (>= $GLIBC)
Installed-Size: $SIZE
Maintainer: $MAINTAINER
Homepage: https://github.com/ViMu475/remote-work-tracker-desktop
Description: Remote Work Tracker - working time and remote quota
 Local web application that tracks working hours, the remote work quota and
 imports SAP time statements. All data stays on this computer.
EOF
    fakeroot dpkg-deb --build --root-owner-group "$T" "$OUT/remote-work-tracker_${VERSION}_amd64.deb" >/dev/null
    echo "built remote-work-tracker_${VERSION}_amd64.deb"
else
    echo "skipped .deb (dpkg-deb or fakeroot missing)"
fi

# ---- .rpm ---------------------------------------------------------------------------------
if command -v rpmbuild >/dev/null; then
    T="$WORK/rpmtree"; install_tree "$T"
    mkdir -p "$WORK/rpm"
    cat > "$WORK/remote-work-tracker.spec" <<EOF
Name:           remote-work-tracker
Version:        $VERSION
Release:        1
Summary:        Working time and remote quota tracker (local web app)
License:        MIT
URL:            https://github.com/ViMu475/remote-work-tracker-desktop
BuildArch:      x86_64
AutoReqProv:    no
Requires:       glibc >= $GLIBC

# the PyInstaller program must not be stripped or repacked
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none

%description
Local web application that tracks working hours, the remote work quota and
imports SAP time statements. All data stays on this computer.

%install
cp -a $T/. %{buildroot}/

%files
/opt/remote-work-tracker
/usr/bin/remote-work-tracker
/usr/share/applications/remote-work-tracker.desktop
/usr/share/icons/hicolor/scalable/apps/remote-work-tracker.svg
%license /usr/share/doc/remote-work-tracker/copyright
EOF
    rpmbuild -bb --quiet --define "_topdir $WORK/rpm" --define "_rpmdir $OUT" \
        --define "_rpmfilename remote-work-tracker-%{version}-%{release}.%{arch}.rpm" \
        "$WORK/remote-work-tracker.spec" 2>/dev/null
    echo "built remote-work-tracker-${VERSION}-1.x86_64.rpm"
else
    echo "skipped .rpm (rpmbuild missing)"
fi
