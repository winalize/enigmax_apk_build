# ENIGMAX FEATURE REGISTRY

Release baseline: 1.5.6 candidate

Critical systems that must be regression-checked on every version:

- App startup / splash
- Force Update: Python detector, HTTP JSON, Java dialog, Play Store URL
- Remote Config: versioning, cache, fallback, refresh
- Match data fetch / parsing / filtering
- MBS / MBS2 daily persistence
- Time filter
- Stats: today/yesterday/30-day refresh, zero-zero repair, post-2026-06-04 continuity
- League quarantine: q.en, automatic quarantine, blacklist, whitelist
- Ads: banner/interstitial, remote switches, daily cap, interval
- Match cards: expand/collapse, scroll stability, detail animation
- Date controls / ALL-LIVE mode
- Review API bridge
- Android Java bridges: AdBridge, ReviewBridge, ForceUpdate, AppKiller, DisclaimerDialog
- Manifest / permissions / AdMob metadata
- Package/version/API/NDK/architecture/build signing
- Android 16 / API 36 compatibility
