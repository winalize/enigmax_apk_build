#!/bin/bash
set -e

echo "🚀 Enigmax APK Build süreci başlatılıyor..."

# 1️⃣ Sistem güncellemeleri
sudo apt-get update -y
sudo apt-get install -y software-properties-common curl unzip wget git zlib1g-dev libffi-dev libssl-dev

# 2️⃣ Java (JDK 17) kurulumu
echo "☕ Java kuruluyor..."
sudo apt-get install -y openjdk-17-jdk

# 3️⃣ Python ve gerekli paketler
echo "🐍 Python ortamı hazırlanıyor..."
sudo apt-get install -y python3 python3-pip python3-dev python3-setuptools
pip install --upgrade pip
pip install buildozer cython virtualenv six setuptools wheel

# 4️⃣ Eksik distutils modülünü kurtarma (bazı ortamlarda ayrı gerekiyor)
python3 -m ensurepip --upgrade || true
pip install setuptools==68.0.0 || true

# 5️⃣ Android SDK kurulumu
echo "📦 Android SDK indiriliyor..."
mkdir -p $HOME/android-sdk && cd $HOME/android-sdk
wget https://dl.google.com/android/repository/commandlinetools-linux-10406996_latest.zip -O cmdline-tools.zip
unzip cmdline-tools.zip -d cmdline-tools
yes | cmdline-tools/cmdline-tools/bin/sdkmanager --licenses
cmdline-tools/cmdline-tools/bin/sdkmanager "platform-tools" "build-tools;33.0.2" "platforms;android-33"
export ANDROID_SDK_ROOT=$HOME/android-sdk
export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools
cd /workspace

# 6️⃣ Buildozer yapılandırması
echo "⚙️ Buildozer başlatılıyor..."
if [ ! -f buildozer.spec ]; then
    buildozer init
fi

# 7️⃣ Derleme işlemi
echo "🛠️ APK derlemesi başlatıldı..."
buildozer -v android debug || { echo "❌ Buildozer derleme başarısız!"; exit 1; }

# 8️⃣ Oluşan APK’yı kontrol et ve göster
echo "🔍 APK dosyası aranıyor..."
APK_PATH=$(find . -name "*.apk" | head -n 1)
if [ -n "$APK_PATH" ]; then
  echo "✅ APK bulundu: $APK_PATH"
else
  echo "⚠️ APK bulunamadı. Build sırasında hata olabilir."
fi

echo "🏁 Build süreci tamamlandı!"
