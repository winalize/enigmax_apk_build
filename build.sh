#!/bin/bash
echo "🚀 Enigmax APK Build süreci başlatılıyor..."

# 1️⃣ Ortam kontrolü
echo "⏳ Python ortamı hazırlanıyor..."
python3 --version || exit 1

# 2️⃣ Gereken Python paketlerini yükle
echo "📦 Buildozer ve bağımlılıkları yükleniyor..."
pip install --upgrade pip setuptools wheel
pip install buildozer cython virtualenv jinja2 sh

# 3️⃣ Buildozer yapılandırması
echo "⚙️ Buildozer yapılandırması kontrol ediliyor..."
if [ ! -f "buildozer.spec" ]; then
    buildozer init
fi

# 4️⃣ Android derleme süreci
echo "🏗️ APK derlemesi başlatılıyor..."
buildozer -v android debug

# 5️⃣ Sonuç bildirimi
if [ -d "bin" ]; then
    echo "✅ Build tamamlandı! APK dosyası aşağıdaki klasörde:"
    ls -lh bin/*.apk 2>/dev/null || echo "⚠️ APK dosyası bulunamadı, build.log'u kontrol et."
else
    echo "❌ Build başarısız oldu, bin klasörü bulunamadı."
fi
