#!/usr/bin/env python3
from pathlib import Path
import re, sys, argparse
ap=argparse.ArgumentParser(); ap.add_argument("--release",action="store_true"); a=ap.parse_args()
s=Path("buildozer.spec").read_text(encoding="utf-8",errors="replace")
expected={"package.name":"enigmax","package.domain":"org.winalize.enigmax","version":"1.5.6","android.numeric_version":"105060000","android.api":"36","android.minapi":"26","android.ndk":"28c","android.ndk_api":"26","android.archs":"arm64-v8a"}
bad=[]
for k,v in expected.items():
 m=re.search(rf"^\s*{re.escape(k)}\s*=\s*(.*?)\s*$",s,re.M); got=m.group(1).strip() if m else None
 if got!=v: bad.append(f"{k}: expected {v}, got {got}")
p=Path("android_src/AndroidManifest.xml")
if p.exists():
 t=p.read_text(encoding="utf-8",errors="replace")
 if 'package="org.winalize.enigmax.enigmax"' not in t: bad.append("Manifest package mismatch")
 if 'android:targetSdkVersion="36"' not in t: bad.append("Manifest targetSdk is not 36")
 if 'android:minSdkVersion="26"' not in t: bad.append("Manifest minSdk is not 26")
h=Path("http_update.py").read_text(encoding="utf-8",errors="replace")
if 'kivy_platform == "android"' not in h: bad.append("Force Update Android detection fix missing")
if a.release:
 m=re.search(r"^\s*android\.release_artifact\s*=\s*(.*?)\s*$",s,re.M)
 if not m or m.group(1).strip()!="aab": bad.append("release_artifact must be aab")
 if not Path("enigmax_release.jks").exists(): bad.append("release keystore missing")
if bad:
 for x in bad: print("::error::"+x)
 sys.exit(1)
print("ENIGMAX CI STATIC GATE: PASS")
print("org.winalize.enigmax.enigmax | 1.5.6 | 105060000 | API36 | min26 | NDK28c | arm64-v8a")
