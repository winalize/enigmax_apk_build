#!/bin/bash
set -e

echo "🚀 Enigmax APK Build süreci başlatılıyor..."

# 1️⃣ Sistem bağımlılıklarını indir (sudo yok, doğrudan apt kullanılacak)
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y curl unzip wget git zlib1g-dev libffi-dev libssl-dev openjdk-17-jdk python3 python3-pip python3-setuptools python3-dev

# 2️⃣ Python ortamını hazırla
echo "🐍 Python ortamı hazırlanıyor..."
pip install --upgrade pip
pip install buildozer cython virtualenv six setuptools wheel

# 3️⃣ distutils düzeltmesi
python3 -m ensurepip --upgrade || true
pip install setuptools==68.0.0 || true

# 4️⃣ Android SDK kurulumu
echo "📦 Android SDK indiriliyor..."
mkdir -p /opt/android-sdk && cd /opt/android-sdk
wget https://dl.google.com/android/repository/commandlinetools-linux-10406996_latest.zip -O cmdline-tools.zip
unzip -q cmdline-tools.zip -d cmdline-tools
yes | cmdline-tools/cmdline-tools/bin/sdkmanager --licenses
cmdline-tools/cmdline-tools/bin/sdkmanager "platform-tools" "build-tools;33.0.2" "platforms;android-33"
export ANDROID_SDK_ROOT=/opt/android-sdk
export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools
cd /opt/render/project/src

# 5️⃣ Buildozer kontrolü
echo "⚙️ Buildozer başlatılıyor..."
if [ ! -f buildozer.spec ]; then
    buildozer init
fi

# 6️⃣ Derleme işlemi
echo "🛠️ APK derlemesi başlatıldı..."
buildozer -v android debug || { echo "❌ Buildozer derleme başarısız!"; exit 1; }

# 7️⃣ Oluşan APK’yı kontrol et
echo "🔍 APK dosyası aranıyor..."
APK_PATH=$(find . -name "*.apk" | head -n 1)
if [ -n "$APK_PATH" ]; then
  echo "✅ APK bulundu: $APK_PATH"
else
  echo "⚠️ APK bulunamadı. Build sırasında hata olabilir."
fi

echo "🏁 Build süreci tamamlandı!"
