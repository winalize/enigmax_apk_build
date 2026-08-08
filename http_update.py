from kivy.app import App
from kivy.clock import Clock
import requests
import sys
from kivy.utils import platform as kivy_platform

# python-for-android can report sys.platform as "linux"; Kivy platform is reliable on Android.
IS_ANDROID = (sys.platform == "android" or kivy_platform == "android")

UPDATE_URL = "https://raw.githubusercontent.com/winalize/enigmax_apk_build/main/update.json"
DEFAULT_STORE_URL = "https://play.google.com/store/apps/details?id=org.winalize.enigmax.enigmax"


def _get_android_version_name(app_version="0.0.0"):
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        pm = activity.getPackageManager()
        pkg = activity.getPackageName()
        info = pm.getPackageInfo(pkg, 0)
        return str(info.versionName)
    except Exception:
        return str(app_version or "0.0.0")


def _vtuple(v):
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _open_store(url):
    if not url:
        return
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")

        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)
    except Exception:
        pass


def check_http_force_update(on_block=None, on_ok=None):
    # PC/desktop testlerinde update sistemi bloklamasin
    if not IS_ANDROID:
        if callable(on_ok):
            try:
                on_ok()
            except Exception:
                pass
        return False

    # Desktop/PC testlerinde force-update bloklamasın
    if not IS_ANDROID:
        if on_ok:
            try:
                on_ok()
            except Exception:
                pass
        return False

    def _ui_ok(_dt):
        if on_ok:
            on_ok()

    def _ui_block(store_url):
        _open_store(store_url or DEFAULT_STORE_URL)
        if on_block:
            on_block()

    try:
        r = requests.get(UPDATE_URL, timeout=12)
        r.raise_for_status()
        data = r.json()

        force = bool(data.get("force_update", False))
        min_v = str(data.get("min_version", "0.0.0"))
        store_url = str(data.get("store_url", ""))

        app = App.get_running_app()
        current = _get_android_version_name(getattr(app, "version", "0.0.0"))

        cur_t = _vtuple(current)
        min_t = _vtuple(min_v)

        print("HTTP_UPDATE current =", current)
        print("HTTP_UPDATE min     =", min_v)
        print("HTTP_UPDATE force   =", force)

        if force and cur_t < min_t:
            print("HTTP_UPDATE → BLOCK")
            Clock.schedule_once(lambda _dt: _ui_block(store_url), 0)
            return

        print("HTTP_UPDATE → OK")
        Clock.schedule_once(_ui_ok, 0)

    except Exception as e:
        print("HTTP_UPDATE ERROR:", e)
        # Force update kontrolü cevap vermezse Android tarafında fail-open yapma.
        # Eski sürümde bu nokta update zorlamasını bypass edebiliyordu.
        Clock.schedule_once(lambda _dt: _ui_block(DEFAULT_STORE_URL), 0)
