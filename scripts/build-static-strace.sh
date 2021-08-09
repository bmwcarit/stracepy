# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

 #!/bin/bash

################################################################################

MYNAME=$(basename $0)
MYDIR=$(dirname $(readlink -f "$0"))
# Check released versions from https://github.com/strace/strace/releases
STRACE_VERSION="5.12"

STRACE_DIR="$MYDIR/strace-bin/"

################################################################################

main () {
    check_command_exists curl
    check_command_exists tar
    check_command_exists make

    # Download
    echo "[+] Downloading strace sources"
    mkdir -p strace-build && cd strace-build
    curl -LO https://github.com/strace/strace/releases/download/v$STRACE_VERSION/strace-$STRACE_VERSION.tar.xz
    check_file_exists strace-$STRACE_VERSION.tar.xz
    tar xJvf strace-$STRACE_VERSION.tar.xz

    # Build static binary for x86_64
    echo "[+] Building static binary"
    cd strace-$STRACE_VERSION
    export CFLAGS="-O2 -static"
    export LDFLAGS="-static -pthread"
    ./configure --disable-mpers --host=x86_64 && make

    # Copy the binary to $STRACE_DIR
    echo "[+] Copying build artifacts to $STRACE_DIR"
    check_file_exists "src/strace"
    mkdir -p $STRACE_DIR
    cp "src/strace" $STRACE_DIR/strace_x86_64

    echo "[+] Done"
}

################################################################################

check_command_exists () {
    if ! [ -x "$(command -v $1)" ]; then
        echo "Error: $1 is not installed" >&2
        exit 1
    fi
}

check_file_exists () {
    if ! [ -f "$1" ]; then
        echo "Error: File not found: \"$1\"" >&2
        exit 1
    fi
}

################################################################################

main "$@"

################################################################################
