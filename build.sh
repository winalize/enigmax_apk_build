#!/bin/bash
echo "🚀 Enigmax APK Build süreci başlatılıyor..."

# Python ve pip hazır mı?
python3 --version || exit 1

# Gereken Python paketleri
echo "📦 Gerekli Python kütüphaneleri yükleniyor..."
pip install --upgrade pip setuptools wheel
pip install buildozer cython virtualenv jinja2 sh

# buildozer.spec varsa dokunma, yoksa oluştur
if [ ! -f "buildozer.spec" ]; then
    echo "⚙️ buildozer.spec dosyası oluşturuluyor..."
    buildozer init
else
    echo "⚙️ buildozer.spec zaten mevcut, devam ediliyor..."
fi

# Android derlemesi
echo "🏗️ APK derlemesi başlatılıyor..."
buildozer -v android debug

# Sonuç
if [ -d "bin" ]; then
    echo "✅ Derleme tamamlandı. APK dosyaları:"
    ls -lh bin/*.apk 2>/dev/null || echo "⚠️ APK bulunamadı, build.log kontrol et."
else
    echo "❌ Derleme başarısız. bin klasörü yok."
fi
