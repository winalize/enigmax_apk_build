from kivy.utils import platform
from kivy.storage.jsonstore import JsonStore
from kivy.app import App
import time
import os

# Android'e özel importlar
if platform == "android":
    from jnius import autoclass
    from android import mActivity
else:
    autoclass = None
    mActivity = None


class ReviewManager:

    STORE_FILE = "review_state.json"

    @classmethod
    def _get_store(cls):
        app = App.get_running_app()
        path = os.path.join(app.user_data_dir, cls.STORE_FILE)
        return JsonStore(path)

    @classmethod
    def check_and_maybe_show(cls):

        # PC’de hiçbir şey yapma
        if platform != "android":
            return

        if not mActivity:
            return

        store = cls._get_store()
        now = int(time.time())

        if not store.exists("review"):
            store.put("review",
                      install_time=now,
                      last_prompt=0,
                      prompted=False)
            return

        data = store.get("review")

        install_time = data.get("install_time", now)
        last_prompt = data.get("last_prompt", 0)
        prompted = data.get("prompted", False)

        # İlk gösterim: 7 gün sonra
        if not prompted:
            if now - install_time >= 7 * 24 * 60 * 60:
                cls._launch_review(store, install_time)
            return

        # Tekrar deneme: 30 gün sonra
        if now - last_prompt >= 30 * 24 * 60 * 60:
            cls._launch_review(store, install_time)

    @classmethod
    def _launch_review(cls, store, install_time):

        if platform != "android":
            return

        if not mActivity:
            return

        try:
            ReviewBridge = autoclass("org.winalize.enigmax.ReviewBridge")
            ReviewBridge.launchReview(mActivity)

            store.put("review",
                      install_time=install_time,
                      last_prompt=int(time.time()),
                      prompted=True)

        except Exception as e:
            print("Review error:", e)