package org.winalize.enigmax;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.LinkedHashMap;
import java.util.Map;

public class DisclaimerDialog {

    public interface AcceptCallback {
        void onAccept(String lang);
    }

    public static void show(
            Activity activity,
            String titleText,
            Map<String, String> disclaimerTexts,
            AcceptCallback callback
    ) {
        activity.runOnUiThread(() -> {

            // ROOT
            LinearLayout root = new LinearLayout(activity);
            root.setOrientation(LinearLayout.VERTICAL);
            root.setPadding(40, 40, 40, 40);
            root.setBackgroundColor(Color.parseColor("#CC000000"));

            // TITLE
            TextView title = new TextView(activity);
            title.setText(titleText);
            title.setTextColor(Color.WHITE);
            title.setTextSize(20);
            title.setPadding(0, 0, 0, 20);
            title.setGravity(Gravity.CENTER);
            root.addView(title);

            // BODY (scrollable)
            ScrollView scroll = new ScrollView(activity);
            LinearLayout.LayoutParams scrollParams =
                    new LinearLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);

            TextView body = new TextView(activity);
            body.setText("");
            body.setTextColor(Color.WHITE);
            body.setTextSize(14);
            body.setPadding(10, 10, 10, 10);

            scroll.addView(body);
            root.addView(scroll, scrollParams);

            // LANGUAGE BUTTONS
            LinearLayout langContainer = new LinearLayout(activity);
            langContainer.setOrientation(LinearLayout.VERTICAL);
            langContainer.setPadding(0, 20, 0, 20);

            root.addView(langContainer);

            CheckBox cb = new CheckBox(activity);
            cb.setText("I have read and accept");
            cb.setTextColor(Color.WHITE);
            cb.setEnabled(false);
            root.addView(cb);

            Button btn = new Button(activity);
            btn.setText("Continue");
            btn.setEnabled(false);
            root.addView(btn);

            final String[] selectedLang = {null};

            Map<String, String> langs = new LinkedHashMap<>();
            langs.put("tr", "Türkçe");
            langs.put("en", "English");
            langs.put("de", "Deutsch");
            langs.put("fr", "Français");
            langs.put("es", "Español");
            langs.put("it", "Italiano");
            langs.put("pt", "Português");
            langs.put("ru", "Русский");

            for (Map.Entry<String, String> e : langs.entrySet()) {
                Button b = new Button(activity);
                b.setText(e.getValue());
                b.setAllCaps(false);
                b.setTextColor(Color.WHITE);
                b.setBackgroundColor(Color.parseColor("#33FFFFFF"));

                b.setOnClickListener(v -> {
                    selectedLang[0] = e.getKey();
                    body.setText(disclaimerTexts.get(e.getKey()));
                    cb.setEnabled(true);
                    cb.setChecked(false);
                    btn.setEnabled(false);
                });

                langContainer.addView(b);
            }

            cb.setOnCheckedChangeListener((c, checked) ->
                    btn.setEnabled(checked && selectedLang[0] != null));

            AlertDialog dialog = new AlertDialog.Builder(activity)
                    .setView(root)
                    .setCancelable(false)
                    .create();

            btn.setOnClickListener(v -> {
                dialog.dismiss();
                if (callback != null && selectedLang[0] != null) {
                    callback.onAccept(selectedLang[0]);
                }
            });

            dialog.show();
        });
    }
}
