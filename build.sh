# --- Upload APK to GitHub ---
echo "Uploading generated APK to GitHub..."
APK_PATH=$(find . -name "*.apk" | head -n 1)
if [ -n "$APK_PATH" ]; then
  echo "Found APK: $APK_PATH"
  git config --global user.email "buildbot@enigmax.ai"
  git config --global user.name "EnigMax-BuildBot"
  git add "$APK_PATH"
  git commit -m "Add generated APK [auto-upload]"
  git push origin main || echo "Git push failed (might be permission issue)"
else
  echo "No APK file found!"
fi
