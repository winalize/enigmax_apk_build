# ENIGMAX RELEASE CHECKLIST — 1.5.6 CANDIDATE

## Automated/static checks completed

- PASS — Python syntax compileall
- PASS — JSON parse integrity
- PASS — package formula: package.domain=org.winalize.enigmax + package.name=enigmax => org.winalize.enigmax.enigmax
- PASS — versionName 1.5.6
- PASS — versionCode 105060000
- PASS — buildozer target API 36
- PASS — custom AndroidManifest targetSdkVersion 36
- PASS — custom AndroidManifest package aligned to org.winalize.enigmax.enigmax
- PASS — min API 26 preserved
- PASS — NDK r28c / ndk_api 26 preserved
- PASS — arm64-v8a preserved
- PASS — Force Update Android detection regression fix preserved
- PASS — Force Update min_version / force_update schema preserved
- PASS — Force Update Play Store URL points to org.winalize.enigmax.enigmax
- PASS — Remote Config bundled schema parses, v=7
- PASS — Ads remote values parse (ap/ad/adm/mv/vi)
- PASS — Time filter remote block parses
- PASS — League quarantine q.en 1/0 unit test
- PASS — Stats 30-day refresh test including zero/zero repair and no hard-coded June 4 cutoff
- PASS — MatchCard no longer forces parent.do_layout() every animation frame
- PASS — Match-card open callback no longer changes scroll_y by -0.10

## Device/build checks required before production

- REQUIRED — Install Android SDK platform 36 in build server
- REQUIRED — Clean API 36 debug APK build
- REQUIRED — Launch test on Android device
- REQUIRED — Force Update low-version test
- REQUIRED — Force Update allowed-version test
- REQUIRED — Match card open/close scroll test (top/middle/bottom of list)
- REQUIRED — Rapid card taps / switching cards
- REQUIRED — Banner/interstitial layout interaction
- REQUIRED — Remote Config online refresh test
- REQUIRED — Stats live network data test, including dates after 2026-06-04
- REQUIRED — MBS/MBS2 persistence today -> yesterday
- REQUIRED — q.en=0 and q.en=1 live remote toggle test
- REQUIRED — Android 16 fullscreen/status/navigation/back behavior
- REQUIRED — Release AAB build
- REQUIRED — jarsigner / bundle manifest verification
- REQUIRED — Play Console test-track acceptance

Production gate: no REQUIRED critical check may remain SKIP/FAIL.

## Audit note

`android_src/src/main/google-services.json` currently declares package_name `org.winalize.enigmax`, while the Play package is `org.winalize.enigmax.enigmax`. No Google Services Gradle plugin/reference was found in the current project, so this file appears inactive. Do not enable Google Services/Firebase with this file until its package registration is corrected.
