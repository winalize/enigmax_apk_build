ENIGMAX 1.5.6 API36 - GITHUB BUILD READY

Bu paket yüklediğiniz TEST CANDIDATE projesinin GitHub Actions eklenmiş tam halidir.

DEBUG:
GitHub > Actions > EnigMax 1.5.6 API36 - Debug APK > Run workflow
Çıktı: Artifacts > ENIGMAX-1.5.6-API36-DEBUG

RELEASE AAB için GitHub Actions Secrets:
ENIGMAX_KEYSTORE_B64
ENIGMAX_KEY_ALIAS
ENIGMAX_KEYSTORE_PASSWORD
ENIGMAX_KEY_PASSWORD

Windows PowerShell keystore base64:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("enigmax_release.jks"))

CI statik olarak şunları bloklar:
package uyuşmazlığı, version/versionCode uyuşmazlığı, API 36/min26/NDK28c/arch uyuşmazlığı,
custom manifest package/targetSdk/minSdk uyuşmazlığı ve Force Update Android detection kaybı.

ÖNEMLİ:
Orijinal buildozer.spec içindeki /opt/android_ndk_r28c yolu DigitalOcean sunucu yoludur.
GitHub workflow build sırasında bunu GitHub runner'daki NDK r28c yoluna geçici olarak çevirir.

GitHub build PASS = release hazır demek değildir.
ENIGMAX SÜRÜM KONTROL PROTOKOLÜ V1 telefon testleri tamamlanmadan production AAB yayınlanmaz.
FAIL = RELEASE YOK
SKIP = RELEASE YOK

V2 GITHUB PATH FIX:
DigitalOcean'a özel /root/winalize_build yolları GitHub Actions sırasında
$GITHUB_WORKSPACE/.buildozer ve $GITHUB_WORKSPACE/bin olarak geçici değiştirilir.
Kaynak buildozer.spec içindeki sunucu ayarları kalıcı olarak değiştirilmez.

V3 SDK/LICENSE FIX:
DigitalOcean'a özel android.sdk_path=/opt/android_sdk değeri GitHub Actions sırasında
$ANDROID_SDK_ROOT olarak değiştirilir. Buildozer/p4a'nın talep ettiği Android SDK
Build-Tools 37.0.0 da önceden kurulur. Target SDK yine 36'dır; build-tools 37
targetSdkVersion değerini değiştirmez.

V4 P4A / SDKMANAGER FIX:
- Buildozer'un kendi klonladığı python-for-android artık v2024.01.21 sürümüne pinlenir.
  Pip ile python-for-android kurmak Buildozer'un klonunu kontrol etmediği için kaldırıldı.
- Buildozer 1.5.0'ın kullandığı legacy $ANDROID_SDK_ROOT/tools/bin/sdkmanager yolu,
  GitHub runner'daki modern cmdline-tools/16.0 sdkmanager'a symlink edilir.
- Böylece Java 17 altında eski sdkmanager'ın javax.xml.bind/XmlSchema hatası engellenir.
- sh paketi stabil p4a hattıyla uyumlu olacak şekilde <2 olarak pinlenir.

V5 PACKAGEDEBUG DIAGNOSTIC FIX:
- buildozer.spec içindeki android.gradle_dependencies satırı tek satır/temiz forma getirildi.
  Önceki biçimde dependency değerlerinin başına literal '\\n' geçiyordu.
- Buildozer packageDebug aşamasında fail ederse workflow otomatik olarak Gradle'ı
  --stacktrace --info ile tekrar çalıştırır.
- gradle-diagnostic.log ve problems-report.html artifact içine eklenir.
Bu değişiklik uygulama iş mantığına dokunmaz.
