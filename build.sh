#!/bin/bash
sudo apt update -y || true
sudo apt install -y openjdk-17-jdk python3-pip autoconf automake libtool pkg-config python3-dev || true
pip install --upgrade pip setuptools wheel
pip install buildozer cython virtualenv
pip install distutils   # ✅ eksik modül burada yükleniyor
buildozer -v android debug
