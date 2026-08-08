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
