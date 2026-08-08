package org.winalize.enigmax;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;

public class AppKiller {
    private static Handler handler = new Handler(Looper.getMainLooper());
    private static Runnable killer;

    public static void scheduleKill(Activity activity, int seconds) {
        cancel();
        killer = () -> {
            activity.finishAffinity(); // TÜM activity’leri kapatır
            System.exit(0);            // Süreci bitirir
        };
        handler.postDelayed(killer, seconds * 1000L);
    }

    public static void cancel() {
        if (killer != null) {
            handler.removeCallbacks(killer);
            killer = null;
        }
    }
}
