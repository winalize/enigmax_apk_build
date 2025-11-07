#!/bin/bash
export PIP_ROOT_USER_ACTION=ignore

echo "🚀 Enigmax APK Build süreci başlatılıyor..."

python3 --version || exit 1

pip install --upgrade pip setuptools wheel --user
pip install buildozer cython virtualenv jinja2 sh --user

if [ ! -f "buildozer.spec" ]; then
    buildozer init
fi

buildozer -v android debug

if [ -d "bin" ]; then
    echo "✅ Derleme tamamlandı. APK dosyaları:"
    ls -lh bin/*.apk
else
    echo "❌ Derleme başarısız, build.log kontrol et."
fi
