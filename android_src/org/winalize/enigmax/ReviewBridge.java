package org.winalize.enigmax;

import android.app.Activity;
import android.util.Log;

import com.google.android.play.core.review.ReviewInfo;
import com.google.android.play.core.review.ReviewManager;
import com.google.android.play.core.review.ReviewManagerFactory;
import com.google.android.gms.tasks.Task;

public class ReviewBridge {

    private static final String TAG = "ReviewBridge";

    public static void launchReview(final Activity activity) {

        if (activity == null) {
            Log.e(TAG, "Activity null");
            return;
        }

        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {

                ReviewManager manager = ReviewManagerFactory.create(activity);
                Task<ReviewInfo> request = manager.requestReviewFlow();

                request.addOnCompleteListener(task -> {

                    if (task.isSuccessful()) {

                        ReviewInfo reviewInfo = task.getResult();
                        manager.launchReviewFlow(activity, reviewInfo)
                               .addOnCompleteListener(task2 ->
                                   Log.d(TAG, "Review flow finished"));

                    } else {
                        Log.e(TAG, "Review request failed");
                    }
                });
            }
        });
    }
}