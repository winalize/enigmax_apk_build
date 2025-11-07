#!/bin/bash

# Render ortamında sudo kullanılamaz, o yüzden Java'yı manuel olarak indiriyoruz
echo "Downloading and setting up OpenJDK 17..."
mkdir -p /tmp/java
curl -L -o /tmp/java/openjdk.tar.gz https://download.java.net/java/GA/jdk17/0d483a2b78e04e6c9ad9a8e9f3b82a58/35/GPL/openjdk-17_linux-x64_bin.tar.gz
tar -xzf /tmp/java/openjdk.tar.gz -C /tmp/java
export JAVA_HOME=/tmp/java/jdk-17
export PATH=$JAVA_HOME/bin:$PATH
java -version

# Python ortamını hazırlıyoruz
pip install --upgrade pip setuptools wheel
pip install buildozer cython virtualenv

# Derleme işlemi
buildozer -v android debug
