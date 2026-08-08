[app]
title = eNigMax
package.name = enigmax
package.domain = org.winalize.enigmax

source.dir = .
source.include_patterns = data/*,utils/*
source.include_exts = py,kv,png,jpg,atlas,gif,json,mp4

android.add_src = android_src

version = 1.5.6
android.numeric_version = 105060000

orientation = portrait
fullscreen = 1

icon.filename = icon.png
presplash.filename = presplash.png

p4a.bootstrap = sdl2

android.archs = arm64-v8a

android.sdk_path = /opt/android_sdk
android.ndk_path = /opt/android_ndk_r28c

android.api = 36
android.minapi = 26
android.ndk = 28c
android.ndk_api = 26

android.enable_androidx = True
android.enable_jetifier = True

android.permissions = INTERNET,ACCESS_NETWORK_STATE,android.permission.AD_ID

requirements = python3==3.9.18,hostpython3==3.9.18,kivy==2.2.1,requests,pillow==10.4.0,pyjnius

android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-6634280715968284~9009912665

android.gradle_dependencies = androidx.appcompat:appcompat:1.6.1,com.google.android.material:material:1.11.0,androidx.gridlayout:gridlayout:1.0.0,com.google.android.gms:play-services-ads:24.9.0,com.google.android.play:review:2.0.2,com.google.android.gms:play-services-tasks:18.2.0

android.build_type = release
android.release_artifact = aab

android.keystore = /root/enigmax/enigmax_release.jks
android.keystore_password = 21011982
android.keyalias = enigmaxkey
android.keyalias_password = 21011982

[buildozer]
warn_on_root = 0
log_level = 2
build_dir = /root/winalize_build/.buildozer
bin_dir = /root/winalize_build/bin