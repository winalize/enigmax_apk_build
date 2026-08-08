package org.winalize.enigmax;

import android.app.Activity;
import android.graphics.Color;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;

import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.AdSize;
import com.google.android.gms.ads.AdView;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.interstitial.InterstitialAd;
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback;
import com.google.android.gms.ads.rewarded.RewardedAd;
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback;

import org.kivy.android.PythonActivity;

public class AdBridge {
    private static final String TAG = "AdBridge";

    // Production AdMob IDs.
    // App ID must also be present in buildozer.spec android.meta_data:
    // com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-6634280715968284~9009912665
    private static final String BANNER_ID = "ca-app-pub-6634280715968284/9130822859";
    // No production interstitial unit was supplied yet. Keep disabled to avoid Google test ads.
    private static final String INTERSTITIAL_ID = "";
    private static final String REWARDED_ID = "ca-app-pub-6634280715968284/7609201083";

    private static InterstitialAd interstitialAd = null;
    private static RewardedAd rewardedAd = null;
    private static AdView bannerAdView = null;
    private static boolean bannerAttached = false;
    private static boolean initialized = false;

    // Full-screen ad accounting flags. These are set only by real SDK callbacks,
    // not when an ad is merely requested. Python uses these to increment counters
    // and start cooldown only after an actual display/reward event.
    private static boolean interstitialDisplayed = false;
    private static boolean rewardedDisplayed = false;
    private static boolean rewardedEarned = false;

    private static Activity activity() {
        try {
            return PythonActivity.mActivity;
        } catch (Exception e) {
            return null;
        }
    }

    private static void ensureInit() {
        Activity a = activity();
        if (a == null || initialized) return;
        initialized = true;
        a.runOnUiThread(() -> {
            try { MobileAds.initialize(a, status -> {}); }
            catch (Exception e) { Log.e(TAG, "MobileAds init failed", e); }
        });
    }

    public static void resetDisplayState() {
        interstitialDisplayed = false;
        rewardedDisplayed = false;
        rewardedEarned = false;
    }

    public static boolean wasInterstitialDisplayed() {
        return interstitialDisplayed;
    }

    public static boolean wasRewardedDisplayed() {
        return rewardedDisplayed || rewardedEarned;
    }

    public static boolean wasAnyFullScreenAdDisplayed() {
        return interstitialDisplayed || rewardedDisplayed || rewardedEarned;
    }

    public static void loadInterstitial() {
        Activity a = activity();
        if (a == null || INTERSTITIAL_ID == null || INTERSTITIAL_ID.length() == 0) return;
        ensureInit();
        a.runOnUiThread(() -> {
            try {
                AdRequest req = new AdRequest.Builder().build();
                InterstitialAd.load(a, INTERSTITIAL_ID, req, new InterstitialAdLoadCallback() {
                    @Override public void onAdLoaded(InterstitialAd ad) { interstitialAd = ad; }
                    @Override public void onAdFailedToLoad(LoadAdError err) { interstitialAd = null; }
                });
            } catch (Exception e) { Log.e(TAG, "loadInterstitial failed", e); }
        });
    }

    public static boolean isInterstitialReady() {
        return interstitialAd != null;
    }

    public static boolean showInterstitial() {
        Activity a = activity();
        if (a == null || INTERSTITIAL_ID == null || INTERSTITIAL_ID.length() == 0 || interstitialAd == null) return false;
        final InterstitialAd ad = interstitialAd;
        interstitialAd = null;
        a.runOnUiThread(() -> {
            try {
                ad.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override public void onAdShowedFullScreenContent() { interstitialDisplayed = true; }
                    @Override public void onAdDismissedFullScreenContent() { loadInterstitial(); }
                    @Override public void onAdFailedToShowFullScreenContent(com.google.android.gms.ads.AdError adError) { loadInterstitial(); }
                });
                ad.show(a);
            } catch (Exception e) {
                Log.e(TAG, "showInterstitial failed", e);
                loadInterstitial();
            }
        });
        return true;
    }

    public static void loadRewarded() {
        Activity a = activity();
        if (a == null) return;
        ensureInit();
        a.runOnUiThread(() -> {
            try {
                AdRequest req = new AdRequest.Builder().build();
                RewardedAd.load(a, REWARDED_ID, req, new RewardedAdLoadCallback() {
                    @Override public void onAdLoaded(RewardedAd ad) { rewardedAd = ad; }
                    @Override public void onAdFailedToLoad(LoadAdError err) { rewardedAd = null; }
                });
            } catch (Exception e) { Log.e(TAG, "loadRewarded failed", e); }
        });
    }

    public static boolean isRewardedReady() {
        return rewardedAd != null;
    }

    public static boolean showRewarded() {
        Activity a = activity();
        if (a == null || rewardedAd == null) return false;
        final RewardedAd ad = rewardedAd;
        rewardedAd = null;
        a.runOnUiThread(() -> {
            try {
                ad.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override public void onAdShowedFullScreenContent() { rewardedDisplayed = true; }
                    @Override public void onAdDismissedFullScreenContent() { loadRewarded(); }
                    @Override public void onAdFailedToShowFullScreenContent(com.google.android.gms.ads.AdError adError) { loadRewarded(); }
                });
                ad.show(a, rewardItem -> { rewardedEarned = true; rewardedDisplayed = true; });
            } catch (Exception e) {
                Log.e(TAG, "showRewarded failed", e);
                loadRewarded();
            }
        });
        return true;
    }

    private static AdSize adaptiveBannerSize(Activity a) {
        try {
            DisplayMetrics dm = a.getResources().getDisplayMetrics();
            float density = dm.density;
            int adWidth = (int) (dm.widthPixels / density);
            if (adWidth <= 0) adWidth = 320;
            return AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(a, adWidth);
        } catch (Exception e) {
            return AdSize.BANNER;
        }
    }

    public static void loadBanner() {
        Activity a = activity();
        if (a == null) return;
        ensureInit();
        a.runOnUiThread(() -> {
            try {
                if (bannerAdView == null) {
                    bannerAdView = new AdView(a);
                    bannerAdView.setAdUnitId(BANNER_ID);
                    bannerAdView.setAdSize(adaptiveBannerSize(a));
                    bannerAdView.setBackgroundColor(Color.TRANSPARENT);
                }
                bannerAdView.loadAd(new AdRequest.Builder().build());
            } catch (Exception e) {
                Log.e(TAG, "loadBanner failed", e);
            }
        });
    }

    public static void showBanner() {
        Activity a = activity();
        if (a == null) return;
        ensureInit();
        a.runOnUiThread(() -> {
            try {
                if (bannerAdView == null) {
                    bannerAdView = new AdView(a);
                    bannerAdView.setAdUnitId(BANNER_ID);
                    bannerAdView.setAdSize(adaptiveBannerSize(a));
                    bannerAdView.setBackgroundColor(Color.TRANSPARENT);
                    bannerAdView.loadAd(new AdRequest.Builder().build());
                }

                ViewGroup parent = (ViewGroup) bannerAdView.getParent();
                if (parent != null && parent != a.getWindow().getDecorView()) {
                    parent.removeView(bannerAdView);
                    bannerAttached = false;
                }

                if (!bannerAttached) {
                    ViewGroup decor = (ViewGroup) a.getWindow().getDecorView();
                    FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                            FrameLayout.LayoutParams.WRAP_CONTENT,
                            FrameLayout.LayoutParams.WRAP_CONTENT,
                            Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL
                    );
                    decor.addView(bannerAdView, lp);
                    bannerAttached = true;
                }
                bannerAdView.setVisibility(View.VISIBLE);
            } catch (Exception e) {
                Log.e(TAG, "showBanner failed", e);
            }
        });
    }

    public static void hideBanner() {
        Activity a = activity();
        if (a == null) return;
        a.runOnUiThread(() -> {
            try {
                if (bannerAdView != null) {
                    bannerAdView.setVisibility(View.GONE);
                }
            } catch (Exception e) {
                Log.e(TAG, "hideBanner failed", e);
            }
        });
    }

    public static boolean showInlineBanner(int slotId) {
        // Kivy owns the visual inline slot. The native AdView is anchored safely at the
        // bottom so existing card layout and scrolling logic are not modified.
        showBanner();
        return true;
    }

    public static boolean showInlineBanner() {
        showBanner();
        return true;
    }
}

