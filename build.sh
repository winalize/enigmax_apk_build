#!/bin/bash
sudo apt update -y
sudo apt install -y openjdk-17-jdk python3-pip autoconf automake libtool pkg-config python3-dev
pip install buildozer cython virtualenv
buildozer init
buildozer -v android debug
