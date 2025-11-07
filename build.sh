#!/bin/bash
set -e

# Python ortamını hazırla
pip install --upgrade pip setuptools wheel
pip install buildozer cython virtualenv

# Java JDK 17 kurulumu (Adoptium)
echo "Installing OpenJDK 17..."
mkdir -p /tmp/jdk
curl -L -o /tmp/jdk/openjdk17.tar.gz https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.11_9.tar.gz
tar -xzf /tmp/jdk/openjdk17.tar.gz -C /tmp/jdk
export JAVA_HOME=$(find /tmp/jdk -type d -name "jdk-17*" | head -n 1)
export PATH=$JAVA_HOME/bin:$PATH

echo "Java version check:"
java -version || echo "Java not found!"

# Derleme başlat
buildozer -v android debug
