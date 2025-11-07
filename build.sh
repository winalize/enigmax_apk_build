#!/bin/bash

# Sistem güncellemesi (Render izin verdiği kadar)
sudo apt-get update -y || true

# Java JDK kurulumu (Android derleme için gerekli)
sudo apt-get install -y openjdk-17-jdk || true

# Python ortamı ve araçlar
pip install --upgrade pip setuptools wheel

# Buildozer ve bağımlılıkları
pip install buildozer cython virtualenv

# distutils modülü artık setuptools içinde, o yüzden ekstra gerek yok
# Ancak pip cache tazelemek için:
pip install --upgrade setuptools

# Derleme
buildozer -v android debug
