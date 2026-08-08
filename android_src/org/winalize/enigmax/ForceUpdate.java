package org.winalize.enigmax;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Simple forced update checker.
 * Expects JSON like:
 * {
 *   "min_version": "1.2.1",
 *   "force": true,
 *   "store_url": "https://play.google.com/store/apps/details?id=org.winalize.enigmax"
 * }
 */
public class ForceUpdate {

    // TODO: Buraya kendi raw update.json linkini koy
    private static final String UPDATE_URL = "https://raw.githubusercontent.com/winalize/enigmax_apk_build/main/update.json";
    private static final String DEFAULT_STORE_URL = "https://play.google.com/store/apps/details?id=org.winalize.enigmax.enigmax";

    public static void check(Activity activity, String currentVersion) {
        new Thread(() -> {
            try {
                JSONObject js = fetchJson(UPDATE_URL);
                if (js == null) {
                    activity.runOnUiThread(() -> showBlockDialog(activity, DEFAULT_STORE_URL));
                    return;
                }

                String min = js.optString("min_version", js.optString("min", ""));
                boolean force = js.optBoolean("force_update", js.optBoolean("force", false));
                String storeUrl = js.optString("store_url", "");

                if (force && isLower(currentVersion, min)) {
                    activity.runOnUiThread(() -> showBlockDialog(activity, storeUrl));
                }
            } catch (Exception ignored) {
                activity.runOnUiThread(() -> showBlockDialog(activity, DEFAULT_STORE_URL));
            }
        }).start();
    }

    private static void showBlockDialog(Activity activity, String url) {
        AlertDialog.Builder b = new AlertDialog.Builder(activity);
        b.setTitle("Update Required");
        b.setMessage("A new version is required to continue.");
        b.setCancelable(false);
        b.setPositiveButton("Update", (d, w) -> {
            try {
                Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                activity.startActivity(i);
            } catch (Exception ignored) {
            }
        });
        b.show();
    }

    private static JSONObject fetchJson(String urlStr) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(6000);
            conn.setReadTimeout(6000);
            conn.setRequestMethod("GET");

            BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line);
            br.close();
            return new JSONObject(sb.toString());
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    // simple semantic compare: "1.2.0" < "1.2.1"
    private static boolean isLower(String a, String b) {
        try {
            String[] A = a.split("\\.");
            String[] B = b.split("\\.");
            int n = Math.max(A.length, B.length);
            for (int i = 0; i < n; i++) {
                int ai = i < A.length ? Integer.parseInt(A[i]) : 0;
                int bi = i < B.length ? Integer.parseInt(B[i]) : 0;
                if (ai < bi) return true;
                if (ai > bi) return false;
            }
            return false;
        } catch (Exception e) {
            return false;
        }
    }
}
