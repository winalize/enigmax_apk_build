import warning
# -- coding: utf-8 --
"""
Enigmax main.py (cleaned)
- FCM / Notification / Topic code removed (per request)
- Keeps: Force update splash + Interstitial ads hook + Core UI
- Fixes: open_external_link on Android now actually opens the URL
- Fixes: Translator cache path no longer overwrites tumcvr.json
"""

import os
import sys
import json
import urllib.request
import random
import datetime
import threading
from datetime import datetime as dt, timedelta
from utils.disclaimer_loader import load_disclaimer

import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.uix.image import Image as KivyImage, AsyncImage
from kivy.uix.video import Video
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.modalview import ModalView
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.animation import Animation
from kivy.resources import resource_find, resource_add_path
from kivy.core.image import Image as CoreImage

# --------- Android bridge (optional) ----------
IS_ANDROID = (sys.platform == "android")
try:
    from jnius import autoclass  # type: ignore
    IS_ANDROID = True
except Exception:
    autoclass = None
    IS_ANDROID = False

# --------- Exit / Focus helpers ----------


# ==================================================
# REMOTE CONFIG VERSIONED UPDATE
# ==================================================
REMOTE_CONFIG_URL = "https://raw.githubusercontent.com/winalize/enigmax-config/main/remote_config.json"

DEFAULT_REMOTE_CONFIG = {
    "v": 1,
    "a": {
        "ap": 1,
        "un": 1,
        "ad": 0,
        "adm": "off",
        "mv": 5,
        "vi": 15
    },
    "m": {
        "fb": 1,
        "lo": 2,
        "hi": 4
    },
    "t": {
        "en": 1,
        "from": "06:45",
        "to": "23:59"
    },
    "q": {
        "en": 1,
        "days": 32,
        "min_rate": 70,
        "min_matches": 5,
        "bl": [],
        "wl": []
    },
    "f": {
        "standard": [310, 380],
        "over_25": [335, 375],
        "home_2_plus": [330, 380],
        "away_2_plus": [330, 385],
        "btts_yes": [340, 390]
    }
}


def _remote_config_path():
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app and getattr(app, "user_data_dir", None):
            return os.path.join(app.user_data_dir, "remote_config.json")
    except Exception:
        pass
    return os.path.join(os.getcwd(), "remote_config.json")


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _read_local_remote_config():
    path = _remote_config_path()
    print("### REMOTE CONFIG LOCAL PATH ###", path)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "v" in data:
                return data
    except Exception as e:
        print("remote_config local read failed:", e)
    return DEFAULT_REMOTE_CONFIG.copy()


def _write_local_remote_config(data):
    path = _remote_config_path()
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        return True
    except Exception as e:
        print("remote_config local write failed:", e)
        return False


def _download_remote_config():
    print("### REMOTE CONFIG URL ###", REMOTE_CONFIG_URL)
    try:
        with urllib.request.urlopen(REMOTE_CONFIG_URL, timeout=6) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if "v" not in data:
            print("### REMOTE CONFIG INVALID: NO VERSION ###")
            return None
        print("### REMOTE CONFIG REMOTE VERSION ###", data.get("v"))
        return data
    except Exception as e:
        print("remote_config download failed:", e)
        return None


def load_remote_config():
    """
    Her uygulama açılışında çağrılır.
    GitHub remote_config.json versiyonu yerelden büyükse yerel config güncellenir.
    Hata durumunda uygulama yerel/default config ile devam eder.
    """
    local_cfg = _read_local_remote_config()
    local_v = _safe_int(local_cfg.get("v"), 0)
    print("### REMOTE CONFIG LOCAL VERSION ###", local_v)

    remote_cfg = _download_remote_config()
    if remote_cfg:
        remote_v = _safe_int(remote_cfg.get("v"), 0)
        if remote_v > local_v:
            if _write_local_remote_config(remote_cfg):
                print("remote_config updated:", local_v, "->", remote_v)
                return remote_cfg
        elif remote_v == local_v:
            print("remote_config already current:", local_v)
        else:
            print("remote_config remote older, local kept:", remote_v, "<", local_v)

    return local_cfg


def decode_remote_odd(encoded_value):
    return (_safe_int(encoded_value, 0) - 200) / 100.0


REMOTE_CONFIG = DEFAULT_REMOTE_CONFIG.copy()
# ==================================================

def disable_focus_borders():
    # Desktop focus rect off (prevents blue focus outline issues)
    try:
        from kivy.utils import platform
        if platform in ("win", "linux", "macosx"):
            from kivy.uix.widget import Widget as _W
            def _block_focus(*args, **kwargs):
                return False
            _W.keyboard_on_focus = _block_focus
    except Exception:
        pass

def exit_app(*_):
    # Android: finish activity; desktop: App.stop + sys.exit
    try:
        if IS_ANDROID and autoclass:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = getattr(PythonActivity, "mActivity", None)
            if activity:
                activity.finish()
                return
    except Exception:
        pass

    try:
        app = App.get_running_app()
        if app:
            app.stop()
    except Exception:
        pass
    raise SystemExit(0)

disable_focus_borders()

# --------- Force update (external module) ----------
from http_update import check_http_force_update  # expects callbacks on_block/on_ok

# --------- App constants ----------
APP_TITLE   = "Winalize"
from kivy.utils import platform

def get_app_version():
    if platform == "android":
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            pm = activity.getPackageManager()
            package_info = pm.getPackageInfo(activity.getPackageName(), 0)
            return package_info.versionName
        except:
            return "Unknown"
    else:
        return "Desktop"

APP_VERSION = f"Enigmax GUI v{get_app_version()}"

DATA_URL    = "https://vd.mackolik.com/livedata?date={d}"   # d: DD/MM/YYYY
LOGO_URL    = "https://im.mackolik.com/img/logo/buyuk/{tid}.gif"
SOURCE_IS_UTC_PLUS3 = True


# --------- Remote Config (GitHub raw, fail-safe) ----------
REMOTE_CONFIG_URL = "https://raw.githubusercontent.com/winalize/enigmax-config/main/remote_config.json"
REMOTE_CONFIG_DEFAULT = {
    "v": 1,
    "a": {"ap": 1, "un": 1, "ad": 0, "adm": "off", "mv": 5, "vi": 15},
    "m": {"fb": 1, "lo": 2, "hi": 4},
    "t": {"en": 1, "from": "06:45", "to": "23:59"},
    "q": {"en": 1, "days": 32, "min_rate": 70, "min_matches": 5, "bl": [], "wl": []},
    "f": {
        "standard": [310, 380],
        "over_25": [335, 375],
        "home_2_plus": [330, 380],
        "away_2_plus": [330, 385],
        "btts_yes": [340, 390],
    },
}

def decode_odd(encoded, default=None):
    try:
        return (float(encoded) - 200.0) / 100.0
    except Exception:
        return default

def _deep_merge_config(base, incoming):
    out = dict(base or {})
    if not isinstance(incoming, dict):
        return out
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_config(out[k], v)
        else:
            out[k] = v
    return out

def _remote_cache_path():
    """
    PC testinde proje/data/remote_config.json dosyasını kullanır.
    Android'de bu yol yazılamazsa user_data_dir/data/remote_config.json alanına düşer.
    """
    try:
        project_data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(project_data_dir, exist_ok=True)
        project_path = os.path.join(project_data_dir, "remote_config.json")

        with open(project_path, "a", encoding="utf-8"):
            pass

        return project_path
    except Exception:
        pass

    try:
        from kivy.app import App
        app = App.get_running_app()
        base = app.user_data_dir if app else "."
        data_dir = os.path.join(base, "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "remote_config.json")
    except Exception:
        return "remote_config.json"

_REMOTE_CONFIG_MEM = {"ts": 0, "cfg": None}

def load_remote_config(force=False):
    """
    Versioned GitHub remote_config loader.
    - PC: data/remote_config.json
    - Android: first data/remote_config.json, if not writable user_data_dir/data/remote_config.json
    - Remote v > local v: update local cache
    - Remote v == local v: keep current cache
    - Remote v < local v: never downgrade
    """
    print("### REMOTE CONFIG START ###")
    cache_path = _remote_cache_path()
    print("### REMOTE CONFIG FILE ###", cache_path)
    print("### REMOTE CONFIG URL ###", REMOTE_CONFIG_URL)

    try:
        now = _now_ts() if "_now_ts" in globals() else 0
        if (not force) and _REMOTE_CONFIG_MEM.get("cfg") is not None and now and (now - int(_REMOTE_CONFIG_MEM.get("ts", 0))) < 300:
            return _REMOTE_CONFIG_MEM.get("cfg")
    except Exception:
        pass

    cfg = _deep_merge_config(REMOTE_CONFIG_DEFAULT, {})
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cfg = _deep_merge_config(cfg, cached)
    except Exception as e:
        print("Remote config cache read failed:", e)

    local_v = int(cfg.get("v", 0) or 0)
    remote_v = None

    try:
        if REMOTE_CONFIG_URL and "OWNER/REPO" not in REMOTE_CONFIG_URL:
            r = requests.get(REMOTE_CONFIG_URL, timeout=6)
            if r.status_code == 200:
                remote = r.json()
                if isinstance(remote, dict) and "v" in remote:
                    remote_v = int(remote.get("v", 0) or 0)
                    print("### REMOTE CONFIG REMOTE VERSION ###", remote_v)
                    if remote_v > local_v:
                        cfg = _deep_merge_config(REMOTE_CONFIG_DEFAULT, remote)
                        try:
                            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                            with open(cache_path, "w", encoding="utf-8") as f:
                                json.dump(cfg, f, ensure_ascii=False, indent=2)
                            print("### REMOTE CONFIG UPDATED ###", local_v, "->", remote_v)
                        except Exception as e:
                            print("Remote config cache write failed:", e)
                    elif remote_v == local_v:
                        print("### REMOTE CONFIG SAME VERSION ###", local_v)
                    else:
                        print("### REMOTE CONFIG DOWNGRADE BLOCKED ###", remote_v, "<", local_v)
                else:
                    print("### REMOTE CONFIG INVALID REMOTE ###")
            else:
                print("### REMOTE CONFIG HTTP STATUS ###", r.status_code)
    except Exception as e:
        print("Remote config fetch failed:", e)

    try:
        print("### REMOTE CONFIG ACTIVE VERSION ###", cfg.get("v"))
        print("### REMOTE CONFIG STANDARD ###", (cfg.get("f", {}) or {}).get("standard"))
    except Exception:
        pass

    try:
        _REMOTE_CONFIG_MEM["cfg"] = cfg
        _REMOTE_CONFIG_MEM["ts"] = _now_ts() if "_now_ts" in globals() else 0
    except Exception:
        pass
    return cfg

def remote_flag(cfg, section, key, default=0):
    try:
        return int((cfg or {}).get(section, {}).get(key, default) or 0)
    except Exception:
        return int(default)

def remote_range(cfg, name, fallback=(1.25, 1.41)):
    try:
        arr = (cfg or {}).get("f", {}).get(name, None)
        if isinstance(arr, (list, tuple)) and len(arr) >= 2:
            lo = decode_odd(arr[0], fallback[0])
            hi = decode_odd(arr[1], fallback[1])
            return float(lo), float(hi)
    except Exception:
        pass
    return fallback

def remote_int(cfg, section, key, default=0):
    try:
        return int((cfg or {}).get(section, {}).get(key, default))
    except Exception:
        return int(default)


# --------- League Quarantine / Blacklist (remote controllable, fail-safe) ----------
def _league_q_cfg(cfg):
    """
    q config:
      en          : 1/0 master switch
      days        : rolling window day count (default 32)
      min_rate    : quarantine threshold percent (default 70)
      min_matches : minimum evaluated matches before auto quarantine (default 5)
      bl          : manual blacklist, items can be "country|league" or "league"
      wl          : manual whitelist override, same format
    """
    q = (cfg or {}).get("q", {}) or {}
    return {
        "en": int(q.get("en", 1) or 0),
        "days": max(1, int(q.get("days", 32) or 32)),
        "min_rate": float(q.get("min_rate", 70) or 70),
        "min_matches": max(1, int(q.get("min_matches", 5) or 5)),
        "bl": q.get("bl", []) if isinstance(q.get("bl", []), list) else [],
        "wl": q.get("wl", []) if isinstance(q.get("wl", []), list) else [],
    }


def league_quarantine_enabled(cfg):
    try:
        return _league_q_cfg(cfg).get("en", 1) == 1
    except Exception:
        return True


def _league_q_norm(v):
    return str(v or "").strip().lower()


def _league_q_key(country, league):
    return (_league_q_norm(country) + "|" + _league_q_norm(league)).strip("|")


def _league_q_match_list(country, league, items):
    key = _league_q_key(country, league)
    lg = _league_q_norm(league)
    for item in items or []:
        it = _league_q_norm(item)
        if not it:
            continue
        if it == key or it == lg:
            return True
    return False


def _league_q_path():
    """Writable quarantine state. Android uses user_data_dir/data, PC falls back to DATA_DIR."""
    try:
        app = App.get_running_app()
        if app and getattr(app, "user_data_dir", None):
            d = os.path.join(app.user_data_dir, "data")
            os.makedirs(d, exist_ok=True)
            return os.path.join(d, "league_quarantine.json")
    except Exception:
        pass
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        return os.path.join(DATA_DIR, "league_quarantine.json")
    except Exception:
        return "league_quarantine.json"


def _league_q_load():
    path = _league_q_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                obj.setdefault("days", {})
                obj.setdefault("quarantine", {})
                return obj
    except Exception as e:
        print("League quarantine load failed:", e)
    return {"days": {}, "quarantine": {}}


def _league_q_save(obj):
    path = _league_q_path()
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print("League quarantine save failed:", e)


def _ddmmyyyy_to_iso(d):
    try:
        return datetime.datetime.strptime(str(d), "%d/%m/%Y").date().isoformat()
    except Exception:
        return str(d or "")


def _league_q_date_cutoff(days):
    try:
        return (datetime.date.today() - datetime.timedelta(days=max(1, int(days)) - 1)).isoformat()
    except Exception:
        return "0000-00-00"


def _league_q_recompute(obj, cfg):
    q = _league_q_cfg(cfg)
    cutoff = _league_q_date_cutoff(q["days"])
    days_obj = obj.get("days", {}) if isinstance(obj.get("days", {}), dict) else {}

    # prune old dates and malformed date keys
    for d in list(days_obj.keys()):
        if str(d) < cutoff:
            days_obj.pop(d, None)

    totals = {}
    for _d, leagues in days_obj.items():
        if not isinstance(leagues, dict):
            continue
        for key, rec in leagues.items():
            if not isinstance(rec, dict):
                continue
            t = totals.setdefault(key, {"success": 0, "fail": 0, "country": rec.get("country", ""), "league": rec.get("league", "")})
            t["success"] += int(rec.get("success", 0) or 0)
            t["fail"] += int(rec.get("fail", 0) or 0)
            if rec.get("country"):
                t["country"] = rec.get("country", "")
            if rec.get("league"):
                t["league"] = rec.get("league", "")

    quarantine = {}
    for key, rec in totals.items():
        total = int(rec.get("success", 0)) + int(rec.get("fail", 0))
        rate = (100.0 * int(rec.get("success", 0)) / total) if total else 0.0
        country = rec.get("country", "")
        league = rec.get("league", "")

        manual_black = _league_q_match_list(country, league, q["bl"])
        manual_white = _league_q_match_list(country, league, q["wl"])
        auto_black = total >= q["min_matches"] and rate < q["min_rate"]

        if (manual_black or auto_black) and not manual_white:
            quarantine[key] = {
                "country": country,
                "league": league,
                "success": int(rec.get("success", 0)),
                "fail": int(rec.get("fail", 0)),
                "total": total,
                "rate": round(rate, 2),
                "reason": "manual" if manual_black else "auto",
                "threshold": q["min_rate"],
                "window_days": q["days"],
            }

    obj["days"] = days_obj
    obj["quarantine"] = quarantine
    return obj


def update_league_quarantine_from_matches(matches, match_date_str, cfg):
    """
    Updates per-league rolling stats from finished MBS1 matches only.
    Important: this runs before UI filtering, so quarantined leagues keep being tracked in the background.
    """
    if not league_quarantine_enabled(cfg):
        return
    day_iso = _ddmmyyyy_to_iso(match_date_str)
    if not day_iso:
        return

    try:
        lo, hi = remote_range(cfg, "standard", (1.25, 1.41))
    except Exception:
        lo, hi = 1.25, 1.41

    day_totals = {}
    for m in matches or []:
        try:
            home = m[2]
            away = m[4]
            token = str(m[6] or "").strip().upper()
            ms_h, ms_a = m[12], m[13]
            time_str = m[16]
            ms1, ms2, o25 = safe_float(m[18]), safe_float(m[20]), safe_float(m[22])
            mbs_raw = str(m[34]).strip()
            lgblk = m[36] if isinstance(m[36], list) else ["", "", "", ""]
            country = lgblk[1] if len(lgblk) > 1 else ""
            league = lgblk[3] if len(lgblk) > 3 else ""

            if not all([home, away, time_str, ms1, ms2, o25, league]):
                continue
            if is_forbidden_time(time_str):
                continue
            if mbs_raw != "1":
                continue
            if o25 is None or not (lo <= o25 <= hi):
                continue
            if token not in ("MS", "UZ", "PEN"):
                continue
            if ms_h is None or ms_a is None:
                continue

            ms_score = f"{int(ms_h)}-{int(ms_a)}"
            tag, _pct = pick_prediction(ms1, ms2, o25)
            ok = eval_outcome(tag, ms_score)
            if ok is None:
                continue

            key = _league_q_key(country, league)
            rec = day_totals.setdefault(key, {"country": country, "league": league, "success": 0, "fail": 0})
            if ok is True:
                rec["success"] += 1
            else:
                rec["fail"] += 1
        except Exception:
            continue

    obj = _league_q_load()
    days_obj = obj.setdefault("days", {})
    if day_totals:
        # Overwrite that day, do not increment. Prevents duplicate counting when the same day is loaded repeatedly.
        days_obj[day_iso] = day_totals
    obj = _league_q_recompute(obj, cfg)
    _league_q_save(obj)


def is_league_quarantined(country, league, cfg=None):
    try:
        if cfg is None:
            cfg = load_remote_config()
        q = _league_q_cfg(cfg)
        if q.get("en", 1) != 1:
            return False
        if _league_q_match_list(country, league, q["wl"]):
            return False
        if _league_q_match_list(country, league, q["bl"]):
            return True
        obj = _league_q_load()
        obj = _league_q_recompute(obj, cfg)
        key = _league_q_key(country, league)
        return key in (obj.get("quarantine", {}) or {})
    except Exception as e:
        print("League quarantine check failed:", e)
        return False


def filter_quarantined_rows(rows, cfg):
    if not league_quarantine_enabled(cfg):
        return rows or []
    out = []
    for r in rows or []:
        try:
            if is_league_quarantined(r.get("country"), r.get("league"), cfg):
                continue
        except Exception:
            pass
        out.append(r)
    return out

def remote_master_ads_enabled(cfg):
    """Master reklam anahtarı. ap=0 ise tüm reklam davranışı kapanır."""
    try:
        a = (cfg or {}).get("a", {}) or {}
        return int(a.get("ap", 1) or 0) == 1
    except Exception:
        return False


def remote_unity_enabled(cfg):
    """Unity Ads / alternatif video ağı anahtarı."""
    try:
        a = (cfg or {}).get("a", {}) or {}
        return remote_master_ads_enabled(cfg) and int(a.get("un", 0) or 0) == 1
    except Exception:
        return False


def remote_admob_enabled(cfg):
    """AdMob backup anahtarı."""
    try:
        a = (cfg or {}).get("a", {}) or {}
        if not remote_master_ads_enabled(cfg):
            return False
        return int(a.get("ad", 0) or 0) == 1 or str(a.get("adm", "off")).lower() == "on"
    except Exception:
        return False


def remote_ads_enabled(cfg):
    """Herhangi bir reklam ağı aktif mi?

    ap=0 => tamamı kapalı.
    un=1 => Unity/alternatif video ağı aktif.
    ad=1 veya adm=on => AdMob backup aktif.
    """
    try:
        return remote_master_ads_enabled(cfg) and (remote_unity_enabled(cfg) or remote_admob_enabled(cfg))
    except Exception:
        return False


def remote_banner_enabled(cfg):
    """Banner anahtarı. Varsayılan: AdMob backup açıksa banner da açıktır.

    GitHub remote_config tarafına ileride a.bn=0/1 eklenirse onu da destekler.
    Mevcut config'i bozmaz; bn yoksa ad/adm değerlerine göre çalışır.
    """
    try:
        a = (cfg or {}).get("a", {}) or {}
        if not remote_master_ads_enabled(cfg):
            return False
        if "bn" in a:
            return int(a.get("bn", 0) or 0) == 1
        return remote_admob_enabled(cfg)
    except Exception:
        return False

# --------- UEFA Theme ----------
Window.clearcolor = (0.0, 0.078, 0.227, 1)  # #00143A
TEXT       = (0.91, 0.95, 1.00, 1)
GREEN      = (0.20, 0.92, 0.25, 1)
RED        = (1.00, 0.35, 0.35, 1)
YELLOW     = (1.00, 0.84, 0.00, 1)
BLUE_SOFT  = (0.75, 0.85, 1.00, 1)
ORANGE     = (1.00, 0.60, 0.20, 1)
GLASS_BLUE = (0.05, 0.12, 0.35, 0.38)
TD_RING    = (1.00, 0.84, 0.00, 1)

FONT_BIG, FONT_MED, FONT_SM = "20sp", "16sp", "14sp"

for p in ("tema", "assets", "data", "."):
    try:
        resource_add_path(p)
    except Exception:
        pass

def find_bg_path():
    for rel in ("tema/icon_bg.png", "assets/icon_bg.png", "data/icon_bg.png", "icon_bg.png"):
        if resource_find(rel) or os.path.exists(rel):
            return rel
    return None

BG_PATH = find_bg_path()

# --------- Translations (tumcvr.json) ----------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


MBS_STATE_FILE = os.path.join(DATA_DIR, "mbs_state.json")


def _load_mbs_state():
    """Load date-based MBS fallback state from data/mbs_state.json."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(MBS_STATE_FILE):
            with open(MBS_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}
        with open(MBS_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_mbs_state(state):
    """Save date-based MBS fallback state to data/mbs_state.json."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(MBS_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state if isinstance(state, dict) else {}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _cleanup_mbs_state(state):
    """Keep only today and yesterday. Future dates are never stored."""
    try:
        keep = {today_str(0), today_str(-1)}
        return {str(k): str(v) for k, v in (state or {}).items() if str(k) in keep and str(v) in ("1", "1,2")}
    except Exception:
        return state if isinstance(state, dict) else {}
try:
    with open(os.path.join(DATA_DIR, "tumcvr.json"), encoding="utf-8") as f:
        _cv = json.load(f)

    UI_STRINGS      = _cv.get("UI_STRINGS", {})
    TRMAP           = _cv.get("TRMAP", {})
    PRED_TEXTS      = _cv.get("PRED_TEXTS", {})
    LABELS          = _cv.get("LABELS", {})
    COUNTRY_EN_MAP  = _cv.get("COUNTRY_EN_MAP", {})
    COUNTRY_TR_MAP  = _cv.get("COUNTRY_TR_MAP", {})
    NOLISAN         = _cv.get("NOLISAN", {})
    BASE_CACHE      = _cv.get("CACHE", {})
except Exception as e:
    print("ÇEVİRİ YÜKLENEMEDİ:", e)
    UI_STRINGS = {}
    TRMAP = {}
    PRED_TEXTS = {}
    LABELS = {}
    COUNTRY_EN_MAP = {}
    COUNTRY_TR_MAP = {}
    NOLISAN = {}
    BASE_CACHE = {}

# Extra UI strings fallback (Stats/Social)
EXTRA_UI_STRINGS = {
    "Statistics": {"en":"Statistics","tr":"İstatistik","de":"Statistik","fr":"Statistiques","it":"Statistiche","es":"Estadísticas","pt":"Estatísticas","ru":"Статистика"},
    "Successful predictions": {"en":"Successful predictions","tr":"Başarılı tahminler","de":"Erfolgreiche Prognosen","fr":"Prédictions réussies","it":"Pronostici riusciti","es":"Pronósticos acertados","pt":"Previsões bem-sucedidas","ru":"Успешные прогнозы"},
    "Failed predictions": {"en":"Failed predictions","tr":"Başarısız tahminler","de":"Fehlgeschlagene Prognosen","fr":"Prédictions échouées","it":"Pronostici falliti","es":"Pronósticos fallidos","pt":"Previsões malsucedidas","ru":"Неудачные прогнозы"},
    "Calculated over the last 30 days.": {"en":"Calculated over the last 30 days.","tr":"Son 30 günün verileri üzerinden hesaplanmıştır.","de":"Basierend auf den letzten 30 Tagen berechnet.","fr":"Calculé sur les 30 derniers jours.","it":"Calcolato sugli ultimi 30 giorni.","es":"Calculado sobre los últimos 30 días.","pt":"Calculado com base nos últimos 30 dias.","ru":"Рассчитано за последние 30 дней."},
    "Social Media": {"en":"Social Media","tr":"Sosyal Medya","de":"Soziale Medien","fr":"Réseaux sociaux","it":"Social Media","es":"Redes Sociales","pt":"Redes Sociais","ru":"Социальные сети"},
}
for _k, _v in EXTRA_UI_STRINGS.items():
    if _k not in UI_STRINGS:
        UI_STRINGS[_k] = _v

# --------- External modules (stats) ----------
from stats_manager import StatsManager, compute_day_from_remote
from utils.review_manager import ReviewManager

# --------- Helpers ----------
LANGS = ["tr", "en", "de", "fr", "it", "es", "pt", "ru"]
DEFAULT_LANG = "en"
DEFAULT_TZ = 0.0  # UTC±0 default

def t_ui(key, lang, **fmt):
    base = UI_STRINGS.get(key, {})
    s = base.get(lang) or base.get("en") or key
    if fmt:
        try:
            s = s.format(**fmt)
        except Exception:
            pass
    return s

def lbl_map(text, lang):
    m = LABELS.get(text)
    if m:
        return m.get(lang, text)
    return text

def open_external_link(url: str):
    try:
        if IS_ANDROID and autoclass:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            activity = getattr(PythonActivity, "mActivity", None)
            if activity is None:
                return
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            activity.startActivity(intent)
        else:
            import webbrowser
            webbrowser.open(url)
    except Exception as e:
        print("Open link error:", e)

def today_str(off=0):
    return (datetime.date.today() + timedelta(days=off)).strftime("%d/%m/%Y")

def build_url(datestr):
    return DATA_URL.format(d=datestr)

def logo_url(team_id):
    return LOGO_URL.format(tid=team_id)

def safe_float(v):
    try:
        f = float(str(v).replace(",", "."))
        if 1.01 <= f <= 20.0:
            return f
    except Exception:
        pass
    return None

def time_to_min(hhmm):
    try:
        h, m = map(int, str(hhmm).split(":"))
        return h * 60 + m
    except Exception:
        return None

def _time_filter_settings(cfg=None):
    """Remote controlled match-time filter.
    Default keeps the previous behavior: allowed 06:45-23:59, forbidden 00:00-06:44.
    Remote config section:
      "t": {"en": 1, "from": "06:45", "to": "23:59"}
    en=0 disables the time filter except invalid/empty times.
    """
    try:
        if cfg is None:
            cfg = load_remote_config()
    except Exception:
        try:
            cfg = REMOTE_CONFIG_DEFAULT
        except Exception:
            cfg = {}
    tcfg = (cfg or {}).get("t", {}) or {}
    try:
        enabled = int(tcfg.get("en", 1) or 0) == 1
    except Exception:
        enabled = True
    start = tcfg.get("from", tcfg.get("start", "06:45"))
    end = tcfg.get("to", tcfg.get("end", "23:59"))
    return enabled, start, end

def is_forbidden_time(hhmm, cfg=None):
    mm = time_to_min(hhmm)
    if mm is None:
        return True

    enabled, start_s, end_s = _time_filter_settings(cfg)
    if not enabled:
        return False

    start_m = time_to_min(start_s)
    end_m = time_to_min(end_s)
    if start_m is None or end_m is None:
        # Fail-safe: previous hard-coded rule.
        return 0 <= mm <= 405  # 00:00-06:45

    # Allowed window may cross midnight.
    if start_m <= end_m:
        return not (start_m <= mm <= end_m)
    return not (mm >= start_m or mm <= end_m)

COUNTRY_SUFFIX_TOKENS = {"U17", "U19", "U20", "U21", "U23", "Women", "(W)"}
COUNTRY_EN_ALIASES = {
    "Bosna Hersek": "Bosnia and Herzegovina",
    "Güney Kore": "South Korea",
    "Kuzey Kore": "North Korea",
    "Kuzey İrlanda": "Northern Ireland",
    "Kuzey Makedonya": "North Macedonia",
    "İrlanda Cumhuriyeti": "Republic of Ireland",
}
COUNTRY_EN_ITEMS = sorted(
    list(((str(k).strip(), str(v).strip()) for k, v in COUNTRY_EN_MAP.items() if str(k).strip()))
    + list(COUNTRY_EN_ALIASES.items()),
    key=lambda kv: len(kv[0]),
    reverse=True,
)


def _split_country_suffixes(text):
    s = (text or "").strip()
    if not s:
        return "", []
    parts = s.split()
    suffixes = []
    while parts and parts[-1] in COUNTRY_SUFFIX_TOKENS:
        suffixes.insert(0, parts.pop())
    return " ".join(parts).strip(), suffixes


def _join_country_suffixes(base, suffixes):
    base = (base or "").strip()
    if suffixes:
        return (base + " " + " ".join(suffixes)).strip()
    return base


def convert_team_name(name, lang="en"):
    if not name:
        return name

    s = str(name).strip().replace("(K)", "(W)")
    base_name, suffixes = _split_country_suffixes(s)

    matched_tr_name = None
    matched_en_name = None
    for tr_name, en_name in COUNTRY_EN_ITEMS:
        if base_name == tr_name:
            matched_tr_name = tr_name
            matched_en_name = en_name
            break

    if matched_tr_name is None:
        return _join_country_suffixes(base_name, suffixes) if suffixes else s

    target_lang = (lang or "en").strip().lower()
    if target_lang == "tr":
        translated_base = matched_tr_name
    elif target_lang == "en":
        translated_base = matched_en_name
    else:
        translated_base = TRANSLATOR.translate_from_tr(matched_tr_name, target_lang) or matched_tr_name

    return _join_country_suffixes(translated_base, suffixes)

# --------- Prediction logic ----------
def pick_prediction(ms1, ms2, o25):
    if 0.99 <= ms1 <= 1.24:
        return "EV2", random.randint(72, 84)
    if 1.00 <= ms2 <= 1.50:
        return "DEP2", random.randint(73, 84)
    if 1.25 <= ms1 <= 1.65:
        return "O25", random.randint(75, 85)
    if ms1 >= 1.85 and ms2 >= 1.85:
        return "KG", random.randint(70, 80)
    return "O25", random.randint(70, 78)

def eval_outcome(tag, ms_score):
    if not ms_score or "-" not in ms_score:
        return None
    try:
        h, a = map(int, ms_score.split("-"))
        if tag == "EV2":
            return h >= 2
        if tag == "DEP2":
            return a >= 2
        if tag == "O25":
            return (h + a) >= 3
        if tag == "KG":
            return (h > 0 and a > 0)
    except Exception:
        pass
    return None

# --------- Translator (hybrid) ----------
class HybridTranslator:
    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.cache = {}
        self._dirty = False
        self._load()

    def _ensure_dir(self):
        d = os.path.dirname(self.cache_path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _load(self):
        base = BASE_CACHE if isinstance(BASE_CACHE, dict) else {}
        self.cache = dict(base)
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                extra = json.load(f)
            if isinstance(extra, dict):
                for key, val in extra.items():
                    if isinstance(val, dict):
                        row = self.cache.get(key, {})
                        row.update(val)
                        self.cache[key] = row
        except Exception:
            pass

    def save(self):
        if not self._dirty:
            return
        self._ensure_dir()
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            self._dirty = False
        except Exception as e:
            print("Cache save error:", e)

    def _get_from_cache(self, text, lang):
        text = (text or "").strip()
        if not text:
            return text
        rec = self.cache.get(text)
        if rec:
            tr = rec.get(lang)
            if tr:
                return tr
        return None

    def _put_to_cache(self, text, lang, translated):
        text = (text or "").strip()
        if not text:
            return
        rec = self.cache.get(text) or {}
        rec[lang] = translated
        self.cache[text] = rec
        self._dirty = True

    def _translate_online(self, text, lang):
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {"client": "gtx", "sl": "auto", "tl": lang, "dt": "t", "q": text}
            r = requests.get(url, params=params, timeout=8)
            arr = r.json()
            if isinstance(arr, list) and arr and isinstance(arr[0], list) and arr[0]:
                chunks = []
                for seg in arr[0]:
                    if seg and isinstance(seg, list) and len(seg) > 0:
                        chunks.append(seg[0])
                if chunks:
                    return "".join(chunks)
        except Exception as e:
            print("translate_online error:", e)
        return text

    def translate(self, text, lang):
        if not text:
            return text

        m = TRMAP.get(text)
        if m:
            return m.get(lang, text)

        ui = UI_STRINGS.get(text)
        if ui:
            return ui.get(lang, text)

        ans = self._get_from_cache(text, lang)
        if ans:
            return ans

        if " - " in text:
            left, right = text.split(" - ", 1)
            lt = self.translate(left, lang)
            rt = self.translate(right, lang)
            comb = f"{lt} - {rt}"
            if comb != text:
                self._put_to_cache(text, lang, comb)
            return comb

        tr = self._translate_online(text, lang)
        if tr and tr != text:
            self._put_to_cache(text, lang, tr)
        return tr


    def _translate_online_tr(self, text, lang):
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {"client": "gtx", "sl": "tr", "tl": lang, "dt": "t", "q": text}
            r = requests.get(url, params=params, timeout=8)
            arr = r.json()
            if isinstance(arr, list) and arr and isinstance(arr[0], list) and arr[0]:
                chunks = []
                for seg in arr[0]:
                    if seg and isinstance(seg, list) and len(seg) > 0:
                        chunks.append(seg[0])
                if chunks:
                    return "".join(chunks)
        except Exception as e:
            print("translate_online_tr error:", e)
        return text

    def translate_from_tr(self, text, lang):
        """Translate assuming the source language is Turkish (TR -> target)."""
        if not text:
            return text

        m = TRMAP.get(text)
        if m:
            return m.get(lang, text)

        ui = UI_STRINGS.get(text)
        if ui:
            return ui.get(lang, text)

        ans = self._get_from_cache(text, lang)
        if ans:
            return ans

        if " - " in text:
            left, right = text.split(" - ", 1)
            lt = self.translate_from_tr(left, lang)
            rt = self.translate_from_tr(right, lang)
            comb = f"{lt} - {rt}"
            if comb != text:
                self._put_to_cache(text, lang, comb)
            return comb

        tr = self._translate_online_tr(text, lang)
        if tr and tr != text:
            self._put_to_cache(text, lang, tr)
        return tr

# IMPORTANT: do NOT point cache_path to tumcvr.json (that would overwrite it)
TRANSLATOR = HybridTranslator(cache_path=os.path.join(DATA_DIR, "trans_cache.json"))

# --------- TZ helpers ----------
TZ_LIST = [
    ("UTC−12", -12), ("UTC−11", -11), ("UTC−10", -10), ("UTC−9",  -9),
    ("UTC−8",  -8),  ("UTC−7",  -7),  ("UTC−6",  -6),  ("UTC−5",  -5),
    ("UTC−4",  -4),  ("UTC−3",  -3),  ("UTC−2",  -2),  ("UTC−1",  -1),
    ("UTC±0",   0),  ("UTC+1",   1),  ("UTC+2",   2),  ("UTC+3",   3),
    ("UTC+4",   4),  ("UTC+5",   5),  ("UTC+6",   6),  ("UTC+7",   7),
    ("UTC+8",   8),  ("UTC+9",   9),  ("UTC+10", 10),  ("UTC+11", 11),
    ("UTC+12", 12),  ("UTC+13", 13),  ("UTC+14", 14),
]

def apply_tz(hhmm_str, user_tz):
    try:
        h, m = map(int, hhmm_str.split(":"))
    except Exception:
        return hhmm_str
    base = dt(2000, 1, 1, h, m)
    if SOURCE_IS_UTC_PLUS3:
        base = base - timedelta(hours=3)
    base = base + timedelta(hours=float(user_tz))
    return base.strftime("%H:%M")

# --------- Logo fallback ----------
def _logo_on_error(instance, error_str):
    ctx = getattr(instance, "_fallback_ctx", None)
    if not ctx or len(ctx) != 1:
        return
    box = ctx[0]
    box.clear_widgets()
    try:
        ci = CoreImage(instance.source, ext='gif')
        box.add_widget(KivyImage(texture=ci.texture, allow_stretch=True, keep_ratio=True))
    except Exception as e:
        print("CoreImage fallback hata:", e)
        ph = KivyImage(source="tema/empty.png", allow_stretch=True, keep_ratio=True)
        box.add_widget(ph)

def get_logo_path(team_id):
    fallback = "data/null_logo.png"
    if not team_id:
        return fallback
    base_dir = os.path.join(DATA_DIR, "logos")
    os.makedirs(base_dir, exist_ok=True)
    png_path = os.path.join(base_dir, f"{team_id}.png")
    if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
        return png_path

    gif_url = logo_url(team_id)
    try:
        r = requests.get(gif_url, timeout=5)
        if r.status_code == 200 and r.content:
            gif_path = os.path.join(base_dir, f"{team_id}.gif")
            with open(gif_path, "wb") as f:
                f.write(r.content)
            try:
                from PIL import Image as PILImage
                im = PILImage.open(gif_path).convert("RGBA")
                im.save(png_path, format="PNG")
                try:
                    os.remove(gif_path)
                except Exception:
                    pass
                return png_path
            except Exception as e:
                print("Logo convert error:", team_id, e)
                return fallback
        else:
            return fallback
    except Exception as e:
        print("Logo download error:", team_id, e)
        return fallback

def logo_widget(team_id, h=68):
    box = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=None, height=dp(h))
    src = get_logo_path(team_id)
    img = AsyncImage(source=src, allow_stretch=True, keep_ratio=True)
    img._fallback_ctx = (box,)
    img.bind(on_error=_logo_on_error)
    box.add_widget(img)
    return box

# --------- Ads hooks ----------
def is_premium():
    """Return True if user has premium flag (ads disabled)."""
    try:
        app = App.get_running_app()
        return bool(app.get_pref("premium", False)) if app else False
    except Exception:
        return False


# --------- Ads Policy (event-based, safe) ----------
# Rules (per user request):
# - Interstitial: daily max 3
# - Minimum 15 minutes between interstitials
# - Session max 1
# - Eligible only after app has been open for 10 seconds
# - Triggered by user interaction (date buttons OR match card tap)
# Notes:
# - Banner click-blocking (24h / 3 clicks) is enforced on the Android (Java) side.

ADS_DAILY_MAX = 5
ADS_MIN_GAP_SECONDS = 15 * 60
ADS_ELIGIBLE_AFTER_OPEN_SECONDS = 10
ADS_TRIGGER_DELAY_SECONDS = 1.2  # 1–2s after user action


def _today_key() -> str:
    try:
        return dt.now().strftime("%Y-%m-%d")
    except Exception:
        return ""


class AdsPolicy:
    """Local, policy-driven interstitial controller using app prefs.json."""

    KEY_DAILY_DATE = "ads_daily_date"
    KEY_DAILY_COUNT = "ads_daily_count"
    KEY_LAST_TS = "ads_last_interstitial_ts"
    KEY_SESSION_SHOWN = "ads_session_interstitial_shown"
    KEY_SESSION_START = "ads_session_start_ts"

    def __init__(self, app: App):
        self.app = app
        self._pending = False
        self.touch_session_start(force=False)

    def touch_session_start(self, force: bool = False) -> None:
        """Mark session start (called on app start)."""
        try:
            if force or (self.app.get_pref(self.KEY_SESSION_START, None) is None):
                self.app.save_pref(self.KEY_SESSION_START, _now_ts())
            # session shown resets at process start
            if force or (self.app.get_pref(self.KEY_SESSION_SHOWN, None) is None):
                self.app.save_pref(self.KEY_SESSION_SHOWN, 0)
        except Exception:
            pass

    def _reset_daily_if_needed(self) -> None:
        try:
            today = _today_key()
            saved = str(self.app.get_pref(self.KEY_DAILY_DATE, ""))
            if saved != today:
                self.app.save_pref(self.KEY_DAILY_DATE, today)
                self.app.save_pref(self.KEY_DAILY_COUNT, 0)
        except Exception:
            pass

    def _daily_count(self) -> int:
        try:
            return int(self.app.get_pref(self.KEY_DAILY_COUNT, 0) or 0)
        except Exception:
            return 0

    def _session_shown(self) -> bool:
        try:
            return bool(int(self.app.get_pref(self.KEY_SESSION_SHOWN, 0) or 0))
        except Exception:
            return False

    def _session_age(self) -> int:
        try:
            start = int(self.app.get_pref(self.KEY_SESSION_START, 0) or 0)
            return max(0, _now_ts() - start)
        except Exception:
            return 0

    def _last_ts(self) -> int:
        try:
            return int(self.app.get_pref(self.KEY_LAST_TS, 0) or 0)
        except Exception:
            return 0

    def can_show_interstitial(self, event_name: str = "") -> bool:
        """Return True if interstitial is allowed right now."""
        if is_premium() or (not IS_ANDROID) or (not autoclass) or (self.app is None):
            return False
        try:
            cfg = load_remote_config()
            if not remote_ads_enabled(cfg):
                return False
        except Exception:
            return False

        self._reset_daily_if_needed()

        # must be open for at least 10s
        if self._session_age() < ADS_ELIGIBLE_AFTER_OPEN_SECONDS:
            return False

        # max 1 per session
        if self._session_shown():
            return False

        cfg = load_remote_config()
        daily_max = max(0, remote_int(cfg, "a", "mv", ADS_DAILY_MAX))
        min_gap = max(0, remote_int(cfg, "a", "vi", 15)) * 60

        # daily cap from remote_config a.mv
        if self._daily_count() >= daily_max:
            return False

        # minimum gap from remote_config a.vi
        last = self._last_ts()
        if last and (_now_ts() - last) < min_gap:
            return False

        return True

    def request_interstitial(self, event_name: str = "") -> None:
        """Request an interstitial after a user interaction."""
        try:
            if self._pending:
                return
            if not self.can_show_interstitial(event_name=event_name):
                return
            self._pending = True

            def _mark_displayed_once() -> None:
                now = _now_ts()
                self.app.save_pref(self.KEY_LAST_TS, now)
                self.app.save_pref(self.KEY_SESSION_SHOWN, 1)
                self._reset_daily_if_needed()
                self.app.save_pref(self.KEY_DAILY_COUNT, self._daily_count() + 1)

            def _confirm_display(*_):
                try:
                    displayed = False
                    try:
                        AdBridge = autoclass("org.winalize.enigmax.AdBridge")
                        for method_name in (
                            "wasAnyFullScreenAdDisplayed",
                            "wasUnityRewardedDisplayed",
                            "wasUnityInterstitialDisplayed",
                            "wasRewardedDisplayed",
                            "wasInterstitialDisplayed",
                        ):
                            if _bridge_bool(AdBridge, method_name, False):
                                displayed = True
                                break
                    except Exception:
                        displayed = False

                    # Critical rule: counters and cooldown start only after a real SDK display/reward callback.
                    if displayed:
                        _mark_displayed_once()
                except Exception as e:
                    print("Interstitial display confirm error:", e)
                finally:
                    self._pending = False

            def _do_show(*_):
                try:
                    if not self.can_show_interstitial(event_name=event_name):
                        self._pending = False
                        return
                    requested = bool(show_interstitial_ad())
                    if requested:
                        Clock.schedule_once(_confirm_display, 2.0)
                    else:
                        try:
                            AdBridge = autoclass("org.winalize.enigmax.AdBridge")
                            AdBridge.loadInterstitial()
                            AdBridge.loadRewarded()
                        except Exception:
                            pass
                        self._pending = False
                except Exception as e:
                    print("Interstitial show error:", e)
                    self._pending = False

            Clock.schedule_once(_do_show, ADS_TRIGGER_DELAY_SECONDS)
        except Exception:
            self._pending = False


# --------- Legacy startup interstitial (disabled) ----------
# Previously, the app scheduled an interstitial on splash->main.
# We now use AdsPolicy + user interaction triggers instead.
AD_DELAY_SECONDS = 10
AD_COOLDOWN_SECONDS = 15 * 60
_LAST_KEY = "last_interstitial_time"  # kept for backward compatibility


def _now_ts() -> int:
    try:
        from time import time as _time
        return int(_time())
    except Exception:
        return 0


def _get_last_interstitial_time(app):
    try:
        if not app:
            return None
        val = app.get_pref(_LAST_KEY, None)
        if val is None:
            return None
        return int(val)
    except Exception:
        return None


def _save_last_interstitial_time(app, ts: int) -> None:
    try:
        if app:
            app.save_pref(_LAST_KEY, int(ts))
    except Exception:
        pass


def _can_show_interstitial(app) -> bool:
    if is_premium() or (not IS_ANDROID) or (not autoclass) or (app is None):
        return False
    last = _get_last_interstitial_time(app)
    if last is None:
        return True
    return (_now_ts() - int(last)) >= AD_COOLDOWN_SECONDS


def _bridge_call(bridge, method_name, default=None):
    """Call a static Java bridge method safely if it exists."""
    try:
        fn = getattr(bridge, method_name, None)
        if not fn:
            return default
        return fn()
    except Exception as e:
        print("AdBridge.%s error:" % method_name, e)
        return default


def _bridge_bool(bridge, method_name, default=False):
    try:
        val = _bridge_call(bridge, method_name, default)
        if val is None:
            return bool(default)
        return bool(val)
    except Exception:
        return bool(default)


def show_interstitial_ad() -> bool:
    """Remote-config kontrollü reklam gösterimi.

    Sayaç burada artırılmaz; AdsPolicy yalnızca bu fonksiyon True dönerse sayaç artırır.
    Öncelik: Unity/alternatif video ağı. AdMob sadece backup olarak çalışır.
    """
    if is_premium() or (not IS_ANDROID) or (not autoclass):
        return False
    try:
        cfg = load_remote_config()
        if not remote_ads_enabled(cfg):
            return False

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = getattr(PythonActivity, "mActivity", None)
        if not activity:
            return False

        AdBridge = autoclass("org.winalize.enigmax.AdBridge")
        _bridge_call(AdBridge, "resetDisplayState", None)

        # 1) Unity / alternatif video ağı. Java tarafında hangi isim eklendiyse onu güvenli dener.
        if remote_unity_enabled(cfg):
            unity_attempts = (
                ("isUnityInterstitialReady", "loadUnityInterstitial", "showUnityInterstitial", "wasUnityInterstitialDisplayed"),
                ("isUnityRewardedReady", "loadUnityRewarded", "showUnityRewarded", "wasUnityRewardedDisplayed"),
                ("isRewardedReady", "loadRewarded", "showRewarded", "wasRewardedDisplayed"),
            )
            for ready_m, load_m, show_m, confirm_m in unity_attempts:
                ready = _bridge_bool(AdBridge, ready_m, None)
                if ready is False:
                    _bridge_call(AdBridge, load_m, None)
                    continue
                shown = _bridge_bool(AdBridge, show_m, False)
                if shown:
                    return True

        # 2) AdMob backup. remote_config: ad=1 veya adm=on ise çalışır.
        if remote_admob_enabled(cfg):
            try:
                if not AdBridge.isInterstitialReady():
                    AdBridge.loadInterstitial()
                    return False
            except Exception:
                pass
            shown = bool(AdBridge.showInterstitial())
            return shown

        return False
    except Exception as e:
        print("Show interstitial error:", e)
        return False


def schedule_startup_ad(app):
    """Schedule interstitial once per process lifetime (after Splash)."""
    try:
        # Disabled by design: event-based ads are safer and avoid open/close spam.
        return
        if getattr(app, "_startup_ad_scheduled", False):
            return
        if not _can_show_interstitial(app):
            return
        setattr(app, "_startup_ad_scheduled", True)

        def _do_show(*_):
            if not _can_show_interstitial(app):
                return
            try:
                show_interstitial_ad()
                _save_last_interstitial_time(app, _now_ts())
            except Exception as e:
                print("Startup interstitial error:", e)

        Clock.schedule_once(_do_show, AD_DELAY_SECONDS)
    except Exception as e:
        print("Startup interstitial schedule error:", e)


# --------- Modal root helper ----------

def _build_modal_root(opacity=0.90, radius=18):
    root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    with root.canvas.before:
        Color(0, 0, 0, opacity)
        root._bg = RoundedRectangle(pos=root.pos, size=root.size, radius=[radius, radius, radius, radius])
    root.bind(pos=lambda *_: setattr(root._bg, "pos", root.pos),
              size=lambda *_: setattr(root._bg, "size", root.size))
    return root

# --------- Flags ----------
FLAG_URLS = {
    "tr": "https://flagcdn.com/h40/tr.png",
    "en": "https://flagcdn.com/h40/gb.png",
    "de": "https://flagcdn.com/h40/de.png",
    "fr": "https://flagcdn.com/h40/fr.png",
    "it": "https://flagcdn.com/h40/it.png",
    "es": "https://flagcdn.com/h40/es.png",
    "pt": "https://flagcdn.com/h40/pt.png",
    "ru": "https://flagcdn.com/h40/ru.png",
}
LANG_LABEL = {"tr":"TR","en":"EN","de":"DE","fr":"FR","it":"IT","es":"ES","pt":"PT","ru":"RU"}

def ensure_flag_path(code):
    url = FLAG_URLS.get(code)
    if not url:
        return ""
    base_dir = os.path.join(DATA_DIR, "flags")
    os.makedirs(base_dir, exist_ok=True)
    fname = os.path.join(base_dir, f"{code}.png")
    if os.path.exists(fname) and os.path.getsize(fname) > 0:
        return fname
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            with open(fname, "wb") as f:
                f.write(r.content)
            return fname
    except Exception as e:
        print("Flag download error:", code, e)
    return url

# --------- UI components ----------
class ClockPill(Label):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.font_size = "20sp"
        self.color = (0.90, 0.95, 1.00, 1)
        self.size_hint = (None, None)
        self.padding_h = dp(18)
        self.padding_v = dp(6)
        self.text = dt.now().strftime("%H:%M:%S")
        self.texture_update()
        w = self.texture_size[0] + self.padding_h * 2
        h = self.texture_size[1] + self.padding_v * 2
        max_w = Window.width * 0.30
        if w > max_w:
            w = max_w
        self.size = (w, h)
        with self.canvas.before:
            Color(0.06, 0.09, 0.20, 0.75)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[16])
            Color(0.25, 0.60, 1.00, 1)
            self._bd = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 16], width=1.4)
        self.bind(pos=self.sync, size=self.sync)
        Clock.schedule_interval(self.tick, 1)

    def tick(self, *_):
        fmt = "%H:%M:%S" if Window.width >= 700 else "%H:%M"
        self.text = dt.now().strftime(fmt)
        self.texture_update()
        w = self.texture_size[0] + self.padding_h * 2
        h = self.texture_size[1] + self.padding_v * 2
        max_w = Window.width * 0.30
        if w > max_w:
            w = max_w
        self.size = (w, h)

    def sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._bd.rounded_rectangle = [self.x, self.y, self.width, self.height, 16]

class AllLiveButton(Button):
    def __init__(self, text, bg_color, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        base_w = dp(46)
        self.size = (min(base_w, Window.width * 0.18), dp(30))
        self.text = text
        self.font_size = "15sp"
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        self.fg_color = (1, 1, 1, 1)
        self.bg_color = bg_color
        self.selected = False
        with self.canvas.before:
            Color(*self.bg_color)
            self._rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
            Color(*(TD_RING if self.selected else (0, 0, 0, 0)))
            self._ring = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 10], width=1.8)
        self.color = self.fg_color
        self.bind(pos=self.sync, size=self.sync)

    def sync(self, *_):
        self._rect.size = self.size
        self._rect.pos = self.pos
        self._ring.rounded_rectangle = [self.x, self.y, self.width, self.height, 10]

    def set_selected(self, val):
        self.selected = bool(val)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            self._rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
            Color(*(TD_RING if self.selected else (0, 0, 0, 0)))
            self._ring = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 10], width=1.8)

class GlassButton(Button):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.active = False
        self.background_normal = ""
        self.background_color = (0.05, 0.17, 0.43, 0.95)
        self.color = TEXT
        self.font_size = "16sp"
        self.size_hint_y = None
        self.height = dp(46)
        self.halign = "center"
        self.valign = "middle"
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))
        with self.canvas.before:
            Color(0.25, 0.60, 1.00, 0.15)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[14])
        self.bind(pos=self.sync, size=self.sync)

    def sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size

    def set_active(self, val):
        self.active = bool(val)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.20, 0.50, 1.00, 0.35 if self.active else 0.15)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[14])

class HeaderButton(ButtonBehavior, BoxLayout):
    pass

class IconButton(ButtonBehavior, Image):
    pass

# --------- Popups ----------

# --- Disclaimer + Language Gate (Kivy UI, Hybrid storage) ---
LANG_DISPLAY = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "tr": "Türkçe",
}

def _sorted_lang_items():
    items = [(LANG_DISPLAY.get(c, c.upper()), c) for c in LANGS]
    items.sort(key=lambda x: x[0].lower())
    return items

class DisclaimerGateView(ModalView):
    """First-run gate: user must pick language and accept disclaimer.

    - UI is pure Kivy (no Android resources / R / Java UI).
    - Stores: prefs.json (primary) + Android SharedPreferences (optional, hybrid).
    """
    def __init__(self, app, on_done, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.on_done = on_done
        self.size_hint = (0.95, 0.92)
        self.auto_dismiss = False

        self.selected_lang = app.get_pref("lang", DEFAULT_LANG) or DEFAULT_LANG
        self._disclaimer = load_disclaimer(self.selected_lang)

        root = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))

        title = Label(text=self._disclaimer.get("title", "Disclaimer"),
                      color=TEXT, font_size="18sp", size_hint_y=None, height=dp(28))
        root.add_widget(title)
        self._title_label = title

        # Text (scroll)
        scroll = ScrollView(size_hint=(1, 0.55))
        body = Label(text=self._disclaimer.get("body", ""),
                     color=TEXT, font_size="14sp",
                     size_hint_y=None, halign="left", valign="top")
        body.bind(
            width=lambda inst, w: setattr(inst, "text_size", (w, None)),
            texture_size=lambda inst, ts: setattr(inst, "height", ts[1] + dp(12)),
        )
        scroll.add_widget(body)
        root.add_widget(scroll)
        self._body_label = body

        # Language selection: all visible (alphabetic)
        root.add_widget(Label(text=t_ui("Language", self.selected_lang),
                              color=TEXT, font_size="14sp", size_hint_y=None, height=dp(22)))

        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        self._lang_buttons = {}
        for disp, code in _sorted_lang_items():
            btn = Button(text=disp, size_hint_y=None, height=dp(38),
                         background_normal="", background_down="",
                         background_color=(0.12, 0.12, 0.12, 1))
            btn.bind(on_release=lambda _b, c=code: self.set_lang(c))
            self._lang_buttons[code] = btn
            grid.add_widget(btn)

        lang_scroll = ScrollView(size_hint=(1, 0.22))
        lang_scroll.add_widget(grid)
        root.add_widget(lang_scroll)

        # Accept row
        accept_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        self.cb = CheckBox(size_hint=(None, None), size=(dp(26), dp(26)))
        accept_row.add_widget(self.cb)
        accept_row.add_widget(Label(text=t_ui("I have read and accept", self.selected_lang),
                                    color=TEXT, font_size="14sp"))
        root.add_widget(accept_row)

        # Continue
        self.continue_btn = Button(text=t_ui("Continue", self.selected_lang),
                                   size_hint_y=None, height=dp(44),
                                   disabled=True)
        self.continue_btn.bind(on_release=self._accept)
        root.add_widget(self.continue_btn)

        self.cb.bind(active=self._on_check)

        self.add_widget(root)
        self._refresh_lang_buttons()

    def _on_check(self, *_):
        self.continue_btn.disabled = not self.cb.active

    def _refresh_lang_buttons(self):
        for code, btn in self._lang_buttons.items():
            btn.background_color = (0.2, 0.6, 0.9, 1) if code == self.selected_lang else (0.12, 0.12, 0.12, 1)

    def set_lang(self, lang_code):
        self.selected_lang = lang_code
        try:
            self._disclaimer = load_disclaimer(self.selected_lang)
        except Exception:
            self._disclaimer = {"title": "Disclaimer", "body": ""}

        self._title_label.text = self._disclaimer.get("title", "Disclaimer")
        self._body_label.text = self._disclaimer.get("body", "")
        self.continue_btn.text = t_ui("Continue", self.selected_lang)
        self._refresh_lang_buttons()

    def _accept(self, *_):
        # Persist language first (selected language becomes app opening language)
        self.app.save_pref("lang", self.selected_lang)

        accepted_at = dt.now().strftime("%d.%m.%Y – %H:%M")

        # Hybrid storage:
        #   - prefs.json (fast gate)
        #   - user_data_dir/data/disclaimer_state.json (durable / single source for About)
        self.app.save_pref("disclaimer_ok", True)  # backward compatible
        self.app.save_pref("disclaimer_accepted", True)
        self.app.save_pref("disclaimer_accepted_at", accepted_at)
        self.app.save_pref("disclaimer_lang", self.selected_lang)
        try:
            self.app.save_disclaimer_state(accepted_at=accepted_at, lang=self.selected_lang)
        except Exception as e:
            print("save_disclaimer_state error:", e)

        # Optional Android SharedPreferences helper (no-op on desktop)
        save_app_language(self.selected_lang)

        # Ensure the main UI reflects the selected language immediately.
        # This recreates only the "main" screen (no lifecycle tricks, no loops).
        try:
            self.app.reload_main()
        except Exception:
            pass

        self.dismiss()
        if callable(self.on_done):
            self.on_done()

class LangPopup(ModalView):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.size_hint = (None, None)
        self.size = (min(Window.width * 0.86, dp(360)), min(Window.height * 0.6, dp(300)))
        self.background = "atlas://data/images/defaulttheme/modalview-background"
        self.background_color = (0, 0, 0, 0)

        root = _build_modal_root(opacity=0.90, radius=18)
        root.size_hint_y = None
        root.bind(minimum_height=root.setter('height'))
        root.orientation = "vertical"
        root.spacing = dp(10)

        title = Label(
            text=t_ui("Language", app.get_pref("lang", DEFAULT_LANG)),
            color=TEXT, font_size="18sp",
            size_hint_y=None, height=dp(28)
        )
        title.halign = "center"
        title.valign = "middle"
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        root.add_widget(title)

        grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, padding=(0, dp(8), 0, dp(4)))
        grid.bind(minimum_height=lambda _, h: setattr(grid, "height", h))

        order = ["de", "en", "__spacer__", "es", "fr", "it", "pt", "ru", "tr"]
        for code in order:
            if code == "__spacer__":
                grid.add_widget(Widget(size_hint_y=None, height=dp(44)))
                continue

            chip = HeaderButton(
                orientation="horizontal",
                padding=dp(6), spacing=dp(4),
                size_hint_y=None, height=dp(44)
            )
            with chip.canvas.before:
                Color(0.08, 0.10, 0.18, 0.95)
                chip._bg = RoundedRectangle(pos=chip.pos, size=chip.size, radius=[12])
            chip.bind(pos=lambda inst, *_: setattr(inst._bg, "pos", inst.pos))
            chip.bind(size=lambda inst, *_: setattr(inst._bg, "size", inst.size))

            fpath = ensure_flag_path(code)
            chip.add_widget(AsyncImage(source=fpath, size_hint=(None, None), size=(dp(30), dp(20)),
                                      allow_stretch=True, keep_ratio=True))

            lab = Label(text=LANG_LABEL.get(code, code.upper()), color=TEXT, size_hint_x=1,
                        halign="left", valign="middle", font_size="14sp")
            lab.bind(size=lambda *_: setattr(lab, "text_size", lab.size))
            chip.add_widget(lab)

            chip.bind(on_release=lambda inst, c=code: self._set_lang(c))
            grid.add_widget(chip)

        root.add_widget(grid)
        self.add_widget(root)

    def _set_lang(self, code):
        self.app.save_pref("lang", code)
        self.dismiss()
        self.app.reload_main()

class TZPopup(ModalView):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.size_hint = (None, None)
        self.size = (dp(330), dp(430))
        self.auto_dismiss = False

        root = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        root.add_widget(Label(text="Universal Time Coordinated", font_size=dp(20), size_hint_y=None,
                              height=dp(40), color=(1, 1, 1, 1)))

        self.selected_tz = app.get_tz()
        self.scroll = ScrollView(size_hint=(1, None), height=dp(280), do_scroll_x=False, do_scroll_y=True, bar_width=0)
        container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        container.bind(minimum_height=container.setter("height"))
        self.scroll.add_widget(container)
        root.add_widget(self.scroll)
        self.container = container
        self._tz_buttons = []

        for name, off in TZ_LIST:
            btn = GlassButton(text=name, size_hint=(1, None), height=dp(44))
            btn.bind(on_release=lambda inst, val=off: self.select_tz(val))
            container.add_widget(btn)
            self._tz_buttons.append(btn)

        self._update_button_states()
        self._center_on_utc_zero()

        apply_btn = GlassButton(text="OK", size_hint=(1, None), height=dp(48))
        apply_btn.bind(on_release=lambda *_: self.apply())
        root.add_widget(apply_btn)
        self.add_widget(root)

    def _center_on_utc_zero(self):
        offs = [off for _, off in TZ_LIST]
        try:
            idx = offs.index(0)
        except ValueError:
            idx = 0
        total = len(offs)
        if total <= 1:
            return
        def do_scroll(*_):
            pos = 1.0 - (idx / max(1, total - 1))
            self.scroll.scroll_y = max(0.0, min(1.0, pos))
        Clock.schedule_once(do_scroll, 0.05)

    def _update_button_states(self):
        for btn, (_, off) in zip(self._tz_buttons, TZ_LIST):
            btn.set_active(float(off) == float(self.selected_tz))

    def select_tz(self, value):
        self.selected_tz = float(value)
        self._update_button_states()

    def apply(self):
        self.app.save_pref("tz", self.selected_tz)
        # Mark as user-defined so auto-detection won't override it later
        self.app.save_pref("tz_user_set", True)
        self.dismiss()
        self.app.reload_main()
        try:
            main = self.app.root.get_screen("main")
            main.lbl_tz.text = main._tz_label_text(self.selected_tz)
        except Exception:
            pass

class StatsPopup(ModalView):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        app_lang = app.get_pref("lang", DEFAULT_LANG)

        self.size_hint = (None, None)
        self.size = (min(Window.width * 0.9, dp(380)), min(Window.height * 0.6, dp(260)))
        self.auto_dismiss = True
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = _build_modal_root(opacity=0.9, radius=18)

        logo_box = AnchorLayout(anchor_x="center", anchor_y="center", size_hint_y=None, height=dp(96))
        try:
            logo_box.add_widget(KivyImage(source="data/ws.png", size_hint=(None, None), size=(dp(72), dp(72)), allow_stretch=True))
        except Exception:
            pass
        root.add_widget(logo_box)

        self.lbl_top = Label(color=TEXT, font_size="24sp", size_hint_y=None, height=dp(32))
        self.lbl_top.halign = "center"
        self.lbl_top.valign = "middle"
        self.lbl_top.bind(size=lambda *_: setattr(self.lbl_top, "text_size", self.lbl_top.size))
        root.add_widget(self.lbl_top)

        self.lbl_succ = Label(text=t_ui("Successful predictions", app_lang) + ": --", color=TEXT, font_size="16sp",
                              size_hint_y=None, height=dp(24))
        self.lbl_succ.halign = "center"
        self.lbl_succ.valign = "middle"
        self.lbl_succ.bind(size=lambda *_: setattr(self.lbl_succ, "text_size", self.lbl_succ.size))
        root.add_widget(self.lbl_succ)

        self.lbl_fail = Label(text=t_ui("Failed predictions", app_lang) + ": --", color=TEXT, font_size="16sp",
                              size_hint_y=None, height=dp(24))
        self.lbl_fail.halign = "center"
        self.lbl_fail.valign = "middle"
        self.lbl_fail.bind(size=lambda *_: setattr(self.lbl_fail, "text_size", self.lbl_fail.size))
        root.add_widget(self.lbl_fail)

        self.lbl_info = Label(text="", color=TEXT, font_size="13sp", size_hint_y=None, height=dp(26))
        self.lbl_info.halign = "center"
        self.lbl_info.valign = "middle"
        self.lbl_info.bind(size=lambda *_: setattr(self.lbl_info, "text_size", self.lbl_info.size))
        root.add_widget(self.lbl_info)

        # --- Loading Image ---
        self.loading_img = Image(
            source="data/loading.png",
            size_hint=(None, None),
            size=(dp(220), dp(70)),
            opacity=0
        )

        loading_box = AnchorLayout(anchor_x="center", anchor_y="center",
                                   size_hint_y=None, height=dp(80))
        loading_box.add_widget(self.loading_img)
        root.add_widget(loading_box)

        self.add_widget(root)
        Clock.schedule_once(lambda *_: self._start_engine(), 0)


    def start_loading(self):
        self.loading_img.opacity = 1
        anim = Animation(opacity=0.2, duration=0.7) + Animation(opacity=1, duration=0.7)
        anim.repeat = True
        anim.start(self.loading_img)
        self._loading_anim = anim

    def stop_loading(self):
        if hasattr(self, "_loading_anim"):
            self._loading_anim.cancel(self.loading_img)
        self.loading_img.opacity = 0

    def _start_engine(self):
        self.start_loading()
        def worker():
            try:
                mgr = StatsManager(DATA_DIR)
                mgr.fill_missing_last_30_days(compute_day_from_remote)
                s, f = mgr.get_totals()
                rate = mgr.get_success_rate()
            except Exception as e:
                print("Stats engine error:", e)
                s, f, rate = 0, 0, 0.0

            def update_ui(_dt):
                self.stop_loading()
                app_lang = self.app.get_pref("lang", DEFAULT_LANG)
                self.lbl_top.text = f"%{rate:.1f}"
                self.lbl_succ.text = t_ui("Successful predictions", app_lang) + f": {s}"
                self.lbl_fail.text = t_ui("Failed predictions", app_lang) + f": {f}"
                self.lbl_info.text = t_ui("Calculated over the last 30 days.", app_lang)

            Clock.schedule_once(update_ui, 0)

        threading.Thread(target=worker, daemon=True).start()

class AboutPopup(ModalView):
    def __init__(self, **kw):
        super().__init__(**kw)

        app = App.get_running_app()
        lang = app.get_pref("lang", DEFAULT_LANG)

        self.size_hint = (None, None)
        self.size = (
            min(Window.width * 0.85, dp(380)),
            min(Window.height * 0.6, dp(300))
        )
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = _build_modal_root(opacity=0.92, radius=18)
        root.spacing = dp(8)
        root.padding = dp(12)

        # --- App info ---
        for t in [
            f"{APP_VERSION}",
            "Winalize Sports © 2026",
            "winalizesports@gmail.com"
        ]:
            lbl = Label(
                text=t,
                color=TEXT,
                font_size="15sp",
                size_hint_y=None,
                height=dp(22),
                halign="center",
                valign="middle"
            )
            lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
            root.add_widget(lbl)

        root.add_widget(Widget(size_hint_y=None, height=dp(8)))

        # --- Disclaimer title (localized) ---
        title = Label(
            text=t_ui("Disclaimer", lang),
            color=TEXT,
            font_size="16sp",
            size_hint_y=None,
            height=dp(26),
            halign="center",
            valign="middle"
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        root.add_widget(title)

        # --- Clickable disclaimer link (localized text) ---
        link = Label(
            text=f"[u][color=4da6ff]{t_ui('View Disclaimer', lang)}[/color][/u]",
            markup=True,
            font_size="13sp",
            size_hint_y=None,
            height=dp(26),
            halign="center",
            valign="middle"
        )
        link.bind(size=lambda *_: setattr(link, "text_size", link.size))

        link.bind(
            on_touch_down=lambda inst, touch:
                open_external_link(
                    "https://winalize.github.io/enigmax_apk_build/disclaimer"
                )
                if inst.collide_point(*touch.pos) else None
        )

        root.add_widget(link)

        # --- Acceptance status (localized, pulled from durable state) ---
        try:
            if app.is_disclaimer_accepted():
                accepted_at = app.get_disclaimer_accepted_at() or ""
                # Use current UI language for the label text
                ui_lang = app.get_pref("lang", DEFAULT_LANG)
                dmeta = load_disclaimer(ui_lang)
                tmpl = (dmeta.get("acceptance_text") or {}).get(ui_lang) or \
                       (dmeta.get("acceptance_text") or {}).get("en") or "Accepted on {date}."
                msg = tmpl.replace("{date}", accepted_at)

                acc = Label(
                    text=msg,
                    color=TEXT,
                    font_size="13sp",
                    size_hint_y=None,
                    height=dp(26),
                    halign="center",
                    valign="middle",
                )
                acc.bind(size=lambda *_: setattr(acc, "text_size", acc.size))
                root.add_widget(acc)
        except Exception as e:
            print("About acceptance status error:", e)
        self.add_widget(root)




class SocialMediaPopup(ModalView):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (min(Window.width * 0.9, dp(380)), min(Window.height * 0.4, dp(200)))
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = _build_modal_root(opacity=0.92, radius=18)
        root.orientation = "vertical"
        root.padding = dp(12)
        root.spacing = dp(10)

        title = Label(text=t_ui("Social Media", app.get_pref("lang", DEFAULT_LANG)), color=TEXT, font_size="18sp",
                      size_hint_y=None, height=dp(28), halign="center", valign="middle")
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        root.add_widget(title)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center", size_hint_y=None, height=dp(80))
        row = BoxLayout(orientation="horizontal", spacing=dp(18), size_hint=(None, None), height=dp(72))

        def icon_btn(img, url):
            btn = Button(background_normal=img, background_down=img, size_hint=(None, None), size=(dp(72), dp(72)), border=(0, 0, 0, 0))
            btn.bind(on_release=lambda *_: open_external_link(url))
            return btn

        row.add_widget(icon_btn("data/tiktok.png", "https://www.tiktok.com/@winalizesports"))
        row.add_widget(icon_btn("data/instagram.png", "https://www.instagram.com/winalize_sports"))
        row.add_widget(icon_btn("data/youtube.png", "https://www.youtube.com/@winalize_sports"))
        row.width = (dp(72) * 3) + (dp(18) * 2)

        anchor.add_widget(row)
        root.add_widget(anchor)

        close_btn = Button(text=t_ui("Close", app.get_pref("lang", DEFAULT_LANG)), size_hint_y=None, height=dp(40))
        close_btn.bind(on_release=lambda *_: self.dismiss())
        root.add_widget(close_btn)

        self.add_widget(root)

class SettingsMenu(ModalView):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.size_hint = (None, None)
        self.size = (min(Window.width * 0.82, dp(330)), min(Window.height * 0.70, dp(350)))
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = _build_modal_root(opacity=0.92, radius=18)
        root.orientation = "vertical"
        root.padding = (dp(10), dp(10))
        root.spacing = dp(6)

        header = Label(text=t_ui("Settings", app.get_pref("lang", DEFAULT_LANG)), color=TEXT, font_size="18sp",
                       size_hint_y=None, height=dp(30))
        header.halign = "center"
        header.valign = "middle"
        header.bind(size=lambda *_: setattr(header, "text_size", header.size))
        root.add_widget(header)

        lang = app.get_pref("lang", DEFAULT_LANG)
        lang_code = LANG_LABEL.get(lang, lang.upper())

        tz = app.get_pref("tz", DEFAULT_TZ)
        tz_text = f"UTC{tz:+g}".replace("+0", "±0")

        def add_btn_custom(text, suffix, func):
            label = t_ui(text.strip(), app.get_pref("lang", DEFAULT_LANG))
            full_text = f"{label} ({suffix})" if suffix else label

            btn = GlassButton(text=full_text, size_hint_y=None, height=dp(42))
            btn.bind(on_release=lambda *_: (self.dismiss(), func()))
            root.add_widget(btn)

        add_btn_custom("", lang_code, lambda: LangPopup(app).open())
        add_btn_custom("", tz_text, lambda: TZPopup(app).open())
        add_btn_custom("Statistics", None, lambda: StatsPopup(app).open())
        add_btn_custom("Social Media", None, lambda: SocialMediaPopup(app).open())
        add_btn_custom("About", None, lambda: AboutPopup().open())


        exit_btn = Button(text=t_ui("Exit App", app.get_pref("lang", DEFAULT_LANG)), size_hint_y=None, height=dp(42),
                          background_normal="", background_color=(0.15, 0.15, 0.15, 1), color=TEXT, font_size="16sp")
        exit_btn.bind(on_release=lambda *_: (self.dismiss(), Clock.schedule_once(lambda __: exit_app(), 0.10)))
        root.add_widget(exit_btn)

        self.add_widget(root)

# --------- Match card ----------

class MatchCard(BoxLayout):
    def __init__(self, m, lang, tz_off, on_toggle_open=None, **kw):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), size_hint_y=None, **kw)
        self.on_toggle_open = on_toggle_open
        self.is_open = False

        self.h_logobox = dp(136)
        self.h_status = dp(28)
        self.h_detail_open = dp(76)
        self.h_detail = 0

        with self.canvas.before:
            Color(1, 1, 1, 0.07)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
        self.bind(pos=self.sync_bg, size=self.sync_bg)

        self.logobox = HeaderButton(orientation="vertical", size_hint_y=None, height=self.h_logobox, padding=dp(8), spacing=dp(6))
        with self.logobox.canvas.before:
            Color(*GLASS_BLUE)
            self._lb_bg = RoundedRectangle(pos=self.logobox.pos, size=self.logobox.size, radius=[12])
        self.logobox.bind(pos=self.sync_lb, size=self.sync_lb)
        self.logobox.bind(on_release=self.toggle)

        row = GridLayout(cols=3, spacing=dp(10), size_hint_y=None, height=self.h_logobox - dp(16))

        col_h = BoxLayout(orientation="vertical", spacing=dp(4))
        col_h.add_widget(logo_widget(m["home_id"], 68))
        hlabel = Label(text=convert_team_name(m["home"], lang), color=TEXT, font_size="14sp", size_hint_y=None, height=dp(40),
                       halign="center", valign="middle")
        hlabel.bind(size=lambda *_: setattr(hlabel, "text_size", hlabel.size))
        col_h.add_widget(hlabel)
        row.add_widget(col_h)

        vsbox = AnchorLayout(anchor_x='center', anchor_y='center')
        vs_img = Image(source="data/vs_ball.png", size_hint=(None, None), size=(dp(63), dp(63)), allow_stretch=False, keep_ratio=True)
        vsbox.add_widget(vs_img)
        row.add_widget(vsbox)

        col_a = BoxLayout(orientation="vertical", spacing=dp(4))
        col_a.add_widget(logo_widget(m["away_id"], 68))
        alabel = Label(text=convert_team_name(m["away"], lang), color=TEXT, font_size="14sp", size_hint_y=None, height=dp(40),
                       halign="center", valign="middle")
        alabel.bind(size=lambda *_: setattr(alabel, "text_size", alabel.size))
        col_a.add_widget(alabel)
        row.add_widget(col_a)

        self.logobox.add_widget(row)
        self.add_widget(self.logobox)

        self.databox = BoxLayout(orientation="vertical", size_hint_y=None, height=self.h_status + self.h_detail, padding=dp(6), spacing=dp(14))
        with self.databox.canvas.before:
            Color(1, 1, 1, 0.04)
            self._db_bg = RoundedRectangle(pos=self.databox.pos, size=self.databox.size, radius=[12])
        self.databox.bind(pos=self.sync_db, size=self.sync_db)

        self.lbl_status = Label(text=m["status_text"], color=m["status_color"], font_size=FONT_MED,
                                size_hint_y=None, height=self.h_status, halign="center", valign="middle")
        self.lbl_status.bind(size=lambda *_: setattr(self.lbl_status, "text_size", self.lbl_status.size))
        self.databox.add_widget(self.lbl_status)

        league_lbl = TRANSLATOR.translate_from_tr(m["league"], lang) if m["league"] else ""
        country_en = COUNTRY_EN_MAP.get(m["country"], m["country"] or "")
        country_lbl = TRANSLATOR.translate(country_en, lang) if country_en else ""
        hour_local = apply_tz(m["time"], tz_off)

        pred_text = PRED_TEXTS.get(lang, PRED_TEXTS.get("en", {})).get(m["suggest_tag"], m["suggest_tag"])

        def lbl_safe(key):
            return LABELS.get(key, {}).get(lang) or LABELS.get(key, {}).get("en") or key

        status_txt = m.get("status_text", "") or ""
        # Percentage visibility must follow the raw match token, not translated status text.
        # Rule: show percentage only before kickoff; hide it once the match has started or ended.
        token_raw = str(m.get("token", "")).strip().upper()
        started_tokens = {"IY", "MS", "UZ", "PEN", "ERT", "YRDK"}
        match_started_or_closed = token_raw.isdigit() or token_raw in started_tokens

        if match_started_or_closed:
            suggest_str = f'* {pred_text} *'
        else:
            suggest_str = f'* {pred_text} * %{m["suggest_pct"]}'

        self.detail = BoxLayout(orientation="vertical", size_hint_y=None, height=self.h_detail, opacity=0)

        top_label = Label(text=league_lbl or "", color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(22),
                          halign="center", valign="middle")
        top_label.bind(size=lambda *_: setattr(top_label, "text_size", top_label.size))
        self.detail.add_widget(top_label)

        line2 = f'{country_lbl}  |  {hour_local}' if country_lbl else hour_local
        mid_label = Label(text=line2, color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(22),
                          halign="center", valign="middle")
        mid_label.bind(size=lambda *_: setattr(mid_label, "text_size", mid_label.size))
        self.detail.add_widget(mid_label)

        self.detail.add_widget(Label(text=suggest_str, color=(1.00, 0.86, 0.25, 1), font_size=FONT_MED,
                                     size_hint_y=None, height=dp(26)))

        # Score line policy:
        # - Not started: do not show any score line
        # - Live / half-time: show only current full-time score as "Score: X - X" in every language
        # - Finished: show normal half-time / full-time result
        token_upper = str(m.get("token", "")).strip().upper()
        is_finished = token_upper in ("MS", "UZ", "PEN")
        is_live = token_upper.isdigit() or token_upper == "IY"
        score_line = ""

        if is_live:
            score_line = f'Score: {m.get("ms_score") or "0-0"}'
        elif is_finished:
            score_line = f'{lbl_map("HT", lang)}: {m.get("iy") or "-"}   |   {lbl_map("FT", lang)}: {m.get("ms_score") or "-"}'

        if score_line:
            self.detail.add_widget(Label(
                text=score_line,
                color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(22)
            ))

        self.databox.add_widget(self.detail)
        self.add_widget(self.databox)
        self._recalc_height()

    def sync_bg(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size

    def sync_lb(self, *_):
        self._lb_bg.pos, self._lb_bg.size = self.logobox.pos, self.logobox.size

    def sync_db(self, *_):
        self._db_bg.pos, self._db_bg.size = self.databox.pos, self.databox.size

    def _recalc_height(self):
        self.height = self.h_logobox + (self.h_status + self.h_detail) + dp(10) + dp(8)

    def toggle(self, *_):
        if self.on_toggle_open:
            self.on_toggle_open(self)

        Animation.cancel_all(self.detail)
        Animation.cancel_all(self)

        if not self.is_open:
            # Ad trigger: match card interaction (event-based interstitial)
            try:
                app = App.get_running_app()
                ads = getattr(app, "ads", None)
                if ads:
                    ads.request_interstitial("match_card")
            except Exception:
                pass
            anim = Animation(height=self.h_detail_open, opacity=1, d=0.20, t='out_cubic')
            anim.bind(on_progress=self.during_anim)
            anim.start(self.detail)
            self.is_open = True
        else:
            anim = Animation(height=0, opacity=0, d=0.18, t='out_cubic')
            anim.bind(on_progress=self.during_anim)
            anim.start(self.detail)
            self.is_open = False

    def during_anim(self, *_):
        # The card height must follow the detail animation, but forcing the
        # parent layout on every animation frame makes ScrollView recalculate
        # its viewport repeatedly and causes the visible list to jump.
        # BoxLayout already observes child size changes and schedules its own
        # layout, so only update this card's dimensions here.
        self.h_detail = self.detail.height
        self.databox.height = self.h_status + self.h_detail
        self._recalc_height()

    def force_close(self):
        if self.is_open:
            Animation.cancel_all(self.detail)
            self.is_open = False
            self.h_detail = 0
            self.detail.height = 0
            self.detail.opacity = 0
            self.databox.height = self.h_status
            self._recalc_height()

# --------- Main screen ----------
class Main(Screen):
    def open_menu(self, *args):
        try:
            SettingsMenu(App.get_running_app()).open()
        except Exception as e:
            print("Menu open error:", e)

    def __init__(self, **kw):
        super().__init__(**kw)
        app = App.get_running_app()
        self.lang = app.get_pref("lang", DEFAULT_LANG)
        self.tz_off = app.get_pref("tz", DEFAULT_TZ)

        self.selected_day = 0
        self.open_card = None
        self.show_mode = "ALL"
        self._active_request_id = 0
        self._request_lock = threading.Lock()
        self._pending_rows = []
        self._render_i = 0

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        with root.canvas.before:
            if BG_PATH:
                Color(1, 1, 1, 1)
                self._bg = Rectangle(source=BG_PATH, pos=root.pos, size=root.size)
            else:
                Color(0, 0, 0, 0)
                self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, "pos", root.pos),
                  size=lambda *_: setattr(self._bg, "size", root.size))

        top = GridLayout(cols=3, size_hint_y=None, height=dp(54), padding=(dp(6), dp(6)), spacing=dp(4))

        mode_cell = AnchorLayout(anchor_x='center', anchor_y='center')
        mode_box = BoxLayout(orientation='horizontal', spacing=dp(4), size_hint=(None, None))
        self.btn_ALL = AllLiveButton("ALL", (0.00, 0.34, 1.00, 1))
        self.btn_ALL.set_selected(True)
        self.btn_ALL.bind(on_release=lambda *_: self._set_mode("ALL"))
        mode_box.add_widget(self.btn_ALL)

        self.btn_LIVE = AllLiveButton("LIVE", (0.85, 0.00, 0.00, 1))
        self.btn_LIVE.bind(on_release=lambda *_: self._set_mode("LIVE"))
        mode_box.add_widget(self.btn_LIVE)

        mode_box.width = self.btn_ALL.width + self.btn_LIVE.width + dp(4)
        mode_box.height = dp(30)
        mode_cell.add_widget(mode_box)
        top.add_widget(mode_cell)

        center_cell = AnchorLayout(anchor_x='center', anchor_y='center')
        self.lbl_clock = ClockPill()
        center_cell.add_widget(self.lbl_clock)
        top.add_widget(center_cell)

        right_cell = AnchorLayout(anchor_x='center', anchor_y='center')
        right_box = BoxLayout(orientation='horizontal', spacing=dp(4), size_hint=(None, None))

        # [REMOVED] UTC/TZ label removed for Warning system
        # Warning Icon (replaces UTC)
        self.warning_icon = IconButton(source="data/yesil.png", size_hint=(None, None), size=(dp(48), dp(48)), allow_stretch=True)
        self.warning_icon.bind(on_release=lambda *_: warning.on_warning_click(self))
        right_box.add_widget(self.warning_icon)

        self.btn_MENU = Button(size_hint=(None, None), size=(dp(36), dp(38)), background_normal="",
                               background_color=(0, 0, 0, 0), border=(0, 0, 0, 0))
        self.btn_MENU.bind(on_release=self.open_menu)

        with self.btn_MENU.canvas.after:
            Color(1, 1, 1, 1)
            h = dp(3)
            self._h1 = Rectangle(size=(dp(26), h))
            self._h2 = Rectangle(size=(dp(26), h))
            self._h3 = Rectangle(size=(dp(26), h))

        def update_hamburger(*_):
            bx, by = self.btn_MENU.pos
            bw, bh = self.btn_MENU.size
            cx = bx + bw/2 - dp(13)
            cy = by + bh/2
            self._h1.pos = (cx, cy + dp(8))
            self._h2.pos = (cx, cy)
            self._h3.pos = (cx, cy - dp(8))

        self.btn_MENU.bind(pos=update_hamburger, size=update_hamburger)
        right_box.add_widget(self.btn_MENU)
        right_box.width = self.btn_MENU.width + dp(4)
        right_box.height = dp(44)

        right_cell.add_widget(right_box)
        top.add_widget(right_cell)
        root.add_widget(top)

        today = datetime.date.today()
        self.dates = {t_ui("Yesterday", self.lang): today - timedelta(days=1),
                      t_ui("Today", self.lang): today,
                      t_ui("Tomorrow", self.lang): today + timedelta(days=1)}
        days = GridLayout(cols=3, size_hint_y=None, height=dp(50), spacing=dp(8))
        self.date_buttons = {}
        for name, dval in self.dates.items():
            b = GlassButton(text=name)
            b.bind(on_release=lambda inst, d=dval, nm=name: self._pick_date(inst, d, nm))
            if name == t_ui("Today", self.lang):
                b.set_active(True)
            days.add_widget(b)
            self.date_buttons[name] = b
        root.add_widget(days)

        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=[0, 0, 0, dp(6)])
        self.list_box.bind(minimum_height=lambda _, h: setattr(self.list_box, "height", h))
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4))
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)

        self.add_widget(root)
        warning.update_warning_icon(self)
        Clock.schedule_once(lambda *_: self.load_and_render(), 0.25)

    def _tz_label_text(self, off):
        o = float(off)
        if o == 0:
            return "UTC±0"
        sign = "+" if o > 0 else "-"
        return f"UTC{sign}{int(abs(o))}"

    def _update_flag_and_tz(self):
        if hasattr(self, "lbl_tz"):
            self.lbl_tz.text = self._tz_label_text(self.tz_off)

    def _new_request_id(self):
        try:
            with self._request_lock:
                self._active_request_id += 1
                return self._active_request_id
        except Exception:
            self._active_request_id += 1
            return self._active_request_id

    def _is_current_request(self, request_id):
        try:
            return int(request_id) == int(getattr(self, "_active_request_id", 0))
        except Exception:
            return False

    def _cancel_render_batches(self):
        self._pending_rows = []
        self._render_i = 0

    def _set_mode(self, m):
        self.show_mode = m
        self.btn_ALL.set_selected(m == "ALL")
        self.btn_LIVE.set_selected(m == "LIVE")
        self.load_and_render()

    def _pick_date(self, btn, dval, name):
        for nm, b in self.date_buttons.items():
            if b is btn:
                b.set_active(True)
                b.text = dval.strftime("%d/%m/%Y")
            else:
                b.set_active(False)
                b.text = nm
        today = datetime.date.today()
        self.selected_day = (dval - today).days
        self.load_and_render()
        # Ad trigger: date button interaction (event-based interstitial)
        try:
            app = App.get_running_app()
            ads = getattr(app, "ads", None)
            if ads:
                ads.request_interstitial("date_button")
        except Exception:
            pass
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 1.0), 0.05)

    def _status_from_token(self, token, tag, ms_score):
        t = str(token).strip().upper()
        if t == "YRDK":
            return (LABELS.get("YARIDA KALDI", {}).get(self.lang, "YARIDA KALDI"), ORANGE)
        if t == "ERT":
            return (LABELS.get("ERTELENDİ", {}).get(self.lang, "ERTELENDİ"), ORANGE)
        if t == "MS":
            ok = eval_outcome(tag, ms_score)
            if ok is True:
                return (LABELS.get("BAŞARILI", {}).get(self.lang, "BAŞARILI"), GREEN)
            if ok is False:
                return (LABELS.get("BAŞARISIZ", {}).get(self.lang, "BAŞARISIZ"), RED)
            return (LABELS.get("MAÇ TAMAMLANDI", {}).get(self.lang, "MAÇ TAMAMLANDI"), TEXT)
        if t in ("UZ", "PEN"):
            ok = eval_outcome(tag, ms_score)
            if ok is True:
                return (LABELS.get("90 dakika sonucu başarılı", {}).get(self.lang, "90 dakika sonucu başarılı"), GREEN)
            else:
                return (LABELS.get("90 dakika sonucu başarısız", {}).get(self.lang, "90 dakika sonucu başarısız"), RED)
        if t == "IY":
            return (LABELS.get("DEVRE ARASI", {}).get(self.lang, "DEVRE ARASI"), YELLOW)
        if t.isdigit():
            base = f"{t} dakika"
            return (TRANSLATOR.translate(base, self.lang), YELLOW)
        return (LABELS.get("HENÜZ BAŞLAMADI", {}).get(self.lang, "HENÜZ BAŞLAMADI"), BLUE_SOFT)

    def _is_live_token(self, token):
        t = str(token).strip().upper()
        return t.isdigit() or (t == "IY")
    # ---------------------------
    # Render helpers (no limit)
    # - Prevents black screen / delayed draw when match count grows
    # - Adds cards in small batches across frames
    # ---------------------------
    def _force_redraw(self, *_):
        try:
            self.list_box.do_layout()
            self.list_box.canvas.ask_update()
            self.scroll.canvas.ask_update()
        except Exception:
            pass

    def _render_rows_incremental(self, rows, request_id=None):
        if request_id is not None and not self._is_current_request(request_id):
            return
        self.list_box.clear_widgets()
        self._pending_rows = rows or []
        self._render_i = 0
        self._render_request_id = request_id

        # Add in small batches to avoid UI freeze / blank frame.
        Clock.schedule_once(lambda dt: self._render_next_batch(dt, request_id), 0)

    def _render_next_batch(self, _dt, request_id=None):
        if request_id is not None and not self._is_current_request(request_id):
            return
        rows = getattr(self, "_pending_rows", [])
        i = int(getattr(self, "_render_i", 0))

        BATCH = 2  # cards per frame (safe on low-end devices)

        for _ in range(BATCH):
            if request_id is not None and not self._is_current_request(request_id):
                return
            if i >= len(rows):
                # Tail spacer for comfortable scroll end
                self.list_box.add_widget(Widget(size_hint_y=None, height=dp(120)))
                self._pending_rows = []
                self._render_i = 0
                Clock.schedule_once(lambda __: setattr(self.scroll, "scroll_y", 1.0), 0.05)
                Clock.schedule_once(self._force_redraw, 0)
                return

            card_number = i + 1
            self.list_box.add_widget(
                MatchCard(rows[i], self.lang, self.tz_off, on_toggle_open=self._set_open_card)
            )
            i += 1

        self._render_i = i
        Clock.schedule_once(self._force_redraw, 0)
        Clock.schedule_once(lambda dt: self._render_next_batch(dt, request_id), 0)


    def _collect_rows_for_mbs(self, matches, allowed_mbs):
        rows = []
        allowed_mbs = {str(x).strip() for x in (allowed_mbs or set())}

        for m in matches:
            try:
                home_id, home = m[1], m[2]
                away_id, away = m[3], m[4]
                token = m[6]
                iy = m[7]
                ms_h, ms_a = m[12], m[13]
                time_str = m[16]
                ms1, ms2, o25 = safe_float(m[18]), safe_float(m[20]), safe_float(m[22])
                mbs_raw = str(m[34]).strip()
                lgblk = m[36] if isinstance(m[36], list) else ["", "", "", ""]
                country = lgblk[1] if len(lgblk) > 1 else ""
                league = lgblk[3] if len(lgblk) > 3 else ""

                if not all([home, away, time_str, ms1, ms2, o25]):
                    continue
                if is_forbidden_time(time_str):
                    continue
                if mbs_raw not in allowed_mbs:
                    continue
                lo, hi = remote_range(load_remote_config(), "standard", (1.25, 1.41))
                if o25 is None or not (lo <= o25 <= hi):
                    continue
                if self.show_mode == "LIVE" and not self._is_live_token(token):
                    continue

                ms_score = f"{ms_h}-{ms_a}" if (ms_h is not None and ms_a is not None) else ""
                tag, pct = pick_prediction(ms1, ms2, o25)
                stxt, scol = self._status_from_token(token, tag, ms_score)

                rows.append(dict(
                    home=home, away=away,
                    home_id=home_id, away_id=away_id,
                    league=league, country=country,
                    time=time_str,
                    iy=iy, ms_score=ms_score, token=token,
                    suggest_tag=tag, suggest_pct=pct,
                    status_text=stxt, status_color=scol
                ))
            except Exception:
                continue

        rows.sort(key=lambda x: (time_to_min(x["time"]) if time_to_min(x["time"]) is not None else 99999))
        return rows

    def _resolve_daily_mbs_mode(self, match_date_str, matches):
        try:
            selected_offset = int(getattr(self, "selected_day", 0) or 0)
        except Exception:
            selected_offset = 0

        # Tomorrow/future: always MBS1 and never write future fallback state.
        if selected_offset > 0:
            return "1"

        cfg = load_remote_config()
        try:
            low_limit = int((cfg.get("m", {}) or {}).get("lo", 2) or 2)
        except Exception:
            low_limit = 2

        state = _cleanup_mbs_state(_load_mbs_state())
        saved = str(state.get(match_date_str, "") or "")

        # Yesterday keeps the exact decision saved when that date was today.
        if selected_offset < 0:
            mode = saved if saved in ("1", "1,2") else "1"
            _save_mbs_state(state)
            return mode

        # Today: once MBS2 opens for this date, it stays open for today and tomorrow-as-yesterday.
        if remote_flag(cfg, "m", "fb", 1) != 1:
            mode = "1"
        elif saved == "1,2":
            mode = "1,2"
        else:
            rows_mbs1 = self._collect_rows_for_mbs(matches, {"1"})
            mbs1_count = len(rows_mbs1)
            mode = "1,2" if mbs1_count <= low_limit else "1"

        state[match_date_str] = mode
        state = _cleanup_mbs_state(state)
        _save_mbs_state(state)

        # Backward compatible debug info only; real source of truth is data/mbs_state.json.
        try:
            app = App.get_running_app()
            if app:
                app.save_pref("mbs_mode", mode)
                app.save_pref("mbs_mode_date", match_date_str)
        except Exception:
            pass

        return mode

    def load_and_render(self):
        request_id = self._new_request_id()
        self._cancel_render_batches()
        self.list_box.clear_widgets()
        d = today_str(self.selected_day)
        info = Label(color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(28))
        info.text = "Yükleniyor..."
        self.list_box.add_widget(info)

        def worker():
            try:
                js = requests.get(build_url(d), timeout=15).json()
                matches = js.get("m", [])
                cfg = load_remote_config()
                # League quarantine update runs before UI filtering, so quarantined leagues keep being tracked in the background.
                try:
                    update_league_quarantine_from_matches(matches, d, cfg)
                except Exception as e:
                    print("League quarantine update skipped:", e)

                mode = self._resolve_daily_mbs_mode(d, matches)
                allowed_mbs = {"1"} if mode == "1" else {"1", "2"}
                rows = self._collect_rows_for_mbs(matches, allowed_mbs)
                rows = filter_quarantined_rows(rows, cfg)
                error_text = None
            except Exception:
                rows = []
                error_text = t_ui("No internet", self.lang)

            def update_ui(_dt):
                if not self._is_current_request(request_id):
                    return
                self.list_box.clear_widgets()
                if error_text:
                    self.list_box.add_widget(Label(text=error_text, color=TEXT, font_size=FONT_MED,
                                                   size_hint_y=None, height=dp(36)))
                    return
                if not rows:
                    self.list_box.add_widget(Widget(size_hint_y=None, height=dp(12)))
                    self.list_box.add_widget(Label(text=t_ui("No suitable matches found.", self.lang), color=TEXT, font_size=FONT_MED,
                                                   size_hint_y=None, height=dp(36)))
                    self.list_box.add_widget(Widget(size_hint_y=None, height=dp(120)))
                    Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 1.0), 0.05)
                    return
                self._render_rows_incremental(rows, request_id=request_id)

            Clock.schedule_once(update_ui, 0)

        threading.Thread(target=worker, daemon=True).start()

    def _set_open_card(self, card):
        if self.open_card and self.open_card is not card:
            self.open_card.force_close()
        self.open_card = card
        # Do not change ScrollView.scroll_y on card taps. The previous delayed
        # -0.10 adjustment caused an intentional viewport jump after every open.
        # The user's current scroll position must remain under direct user control.

# --------- Splash screen ----------
class Splash(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._allow = False
        self._blocked = False
        self._splash_done = False
        self._update_answered = False
        self._video = None
        self._poster = None
        self._ui_built = False
        self._intro_path = os.path.join("data", "intro.mp4")
        self._poster_path = os.path.join("data", "presplash.png")
        self._has_intro = False
        self._splash_delay = 3.5

        Clock.schedule_once(self._mark_splash_done, self._splash_delay)
        Clock.schedule_once(self._update_timeout, 12.0)


    def _sync_splash_bg(self, *_):
        try:
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size
        except Exception:
            pass

    def _build_visual(self):
        if self._ui_built:
            return

        self._ui_built = True
        self.clear_widgets()

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._sync_splash_bg, size=self._sync_splash_bg)

        fallback = self._poster_path if os.path.exists(self._poster_path) else "icon.png"

        holder = AnchorLayout(anchor_x="center", anchor_y="center")

        self._poster = KivyImage(
            source=fallback,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1)
        )

        holder.add_widget(self._poster)
        self.add_widget(holder)

    def on_pre_enter(self, *args):
        self._build_visual()
        return super().on_pre_enter(*args)

    def on_enter(self):
        print("### SPLASH ENTERED ###")
        check_http_force_update(on_block=self._on_block, on_ok=self._on_ok)

    def on_leave(self, *args):
        if self._video:
            try:
                self._video.state = "stop"
            except Exception:
                pass
        return super().on_leave(*args)

    def _on_video_error(self, *_):
        try:
            self._video = None
            self.clear_widgets()
            fallback = self._poster_path if os.path.exists(self._poster_path) else "icon.png"
            self._poster = KivyImage(source=fallback, allow_stretch=True, keep_ratio=True)
            self.add_widget(self._poster)
        except Exception as e:
            print("Splash fallback image error:", e)

    def _on_video_eos(self, *_):
        if self._video and not self._splash_done:
            try:
                self._video.state = "stop"
                self._video.position = 0
                self._video.state = "play"
            except Exception:
                pass

    def _on_ok(self):
        print("### UPDATE OK ###")
        self._update_answered = True
        self._allow = True
        self._try_go_next()

    def _on_block(self):
        print("### UPDATE REQUIRED → BLOCK ###")
        self._update_answered = True
        self._blocked = True
        self._allow = False

    def _mark_splash_done(self, *_):
        self._splash_done = True
        self._try_go_next()

    def _update_timeout(self, *_):
        if not self._update_answered:
            print("### UPDATE TIMEOUT → BLOCK / WAIT ###")
            self._update_answered = True
            self._blocked = True
            self._allow = False

    def _try_go_next(self):
        if self._blocked or (not self._splash_done) or (not self._allow):
            return
        app = App.get_running_app()

        # --- Disclaimer gate (Kivy, first-run) ---
        if app and (not app.is_disclaimer_accepted()):
            if not getattr(self, "_disclaimer_shown", False):
                self._disclaimer_shown = True

                def _after_disclaimer():
                    # Re-evaluate conditions and continue flow
                    self._try_go_next()

                try:
                    DisclaimerGateView(app, on_done=_after_disclaimer).open()
                except Exception as e:
                    print("Disclaimer gate error:", e)
                    # Fail open (never brick app)
                    _after_disclaimer()
            return
        # Startup interstitial is intentionally disabled.
        if self._video:
            try:
                self._video.state = "stop"
            except Exception:
                pass
        if app and app.root:
            app.root.current = "main"

# --------- App ----------

# -------------------------------------------------
# LOGO CACHE CLEANUP (Sentinel)
# Max 150 logo, oldest removed on app start
# -------------------------------------------------
def trim_logo_cache(max_files=150):
    try:
        logo_dir = os.path.join(DATA_DIR, "logos")
        if not os.path.isdir(logo_dir):
            return

        files = [
            os.path.join(logo_dir, f)
            for f in os.listdir(logo_dir)
            if f.lower().endswith(".png")
        ]

        if len(files) <= max_files:
            return

        # sort by modification time (oldest first)
        files.sort(key=lambda p: os.path.getmtime(p))

        # remove excess files
        for p in files[:-max_files]:
            try:
                os.remove(p)
            except Exception:
                pass
    except Exception:
        # never crash the app because of cache cleanup
        pass


class EnigmaxApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bg_kill_event = None

    title = APP_TITLE

    def get_pref_path(self):
        os.makedirs(self.user_data_dir, exist_ok=True)
        return os.path.join(self.user_data_dir, "prefs.json")

    def load_prefs(self):
        try:
            with open(self.get_pref_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_pref(self, key, val):
        prefs = self.load_prefs()
        prefs[key] = val
        with open(self.get_pref_path(), "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)

    def get_pref(self, key, default=None):
        return self.load_prefs().get(key, default)

    def get_tz(self):
        return float(self.get_pref("tz", 0.0))

    # ----------------- Disclaimer state (durable JSON) -----------------
    def _disclaimer_state_dir(self):
        """Writable location for durable disclaimer acceptance state."""
        base = self.user_data_dir
        d = os.path.join(base, "data")
        os.makedirs(d, exist_ok=True)
        return d

    def get_disclaimer_state_path(self):
        return os.path.join(self._disclaimer_state_dir(), "disclaimer_state.json")

    def load_disclaimer_state(self):
        try:
            with open(self.get_disclaimer_state_path(), "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def save_disclaimer_state(self, accepted_at: str, lang: str):
        state = {"accepted": True, "accepted_at": accepted_at, "lang": lang}
        with open(self.get_disclaimer_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def is_disclaimer_accepted(self) -> bool:
        # Primary: durable state file
        st = self.load_disclaimer_state()
        if st.get("accepted") is True:
            return True
        # Secondary: prefs (backward compatibility)
        return bool(self.get_pref("disclaimer_accepted", False) or self.get_pref("disclaimer_ok", False))

    def get_disclaimer_accepted_at(self) -> str:
        st = self.load_disclaimer_state()
        if st.get("accepted") is True and st.get("accepted_at"):
            return str(st.get("accepted_at"))
        return str(self.get_pref("disclaimer_accepted_at", "") or self.get_pref("disclaimer_time", ""))

    def get_disclaimer_lang(self) -> str:
        st = self.load_disclaimer_state()
        if st.get("accepted") is True and st.get("lang"):
            return str(st.get("lang"))
        return str(self.get_pref("disclaimer_lang", "") or self.get_pref("lang", DEFAULT_LANG))

    # ----------------- Device UTC auto-detection -----------------
    def detect_device_utc_offset_hours(self) -> float:
        """Detect current device UTC offset in hours (e.g., +3.0)."""
        try:
            off = dt.now().astimezone().utcoffset()
            if off is None:
                return 0.0
            return round(off.total_seconds() / 3600.0, 2)
        except Exception:
            return 0.0

    def build(self):
        print("### REMOTE CONFIG LOAD START ###")
        global REMOTE_CONFIG
        REMOTE_CONFIG = load_remote_config()
        print("### REMOTE CONFIG ACTIVE VERSION ###", REMOTE_CONFIG.get("v"))
        print("### REMOTE CONFIG STANDARD ###", (REMOTE_CONFIG.get("f", {}) or {}).get("standard"))
        # Sentinel: clean logo cache once at app start
        trim_logo_cache()

        if self.get_pref("lang") is None:
            self.save_pref("lang", DEFAULT_LANG)

        # TZ: auto-detect from device UTC unless user explicitly chose a TZ before
        if self.get_pref("tz") is None:
            self.save_pref("tz", DEFAULT_TZ)
        if not bool(self.get_pref("tz_user_set", False)):
            try:
                self.save_pref("tz", float(self.detect_device_utc_offset_hours()))
            except Exception:
                pass

        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(Splash(name="splash"))
        sm.add_widget(Main(name="main"))
        sm.current = "splash"
        return sm


    def on_start(self):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: ReviewManager.check_and_maybe_show(), 5)

        # Refresh rolling stats in the background on every app start.
        # The stats popup still reads the same data, but the file no longer waits
        # for the user to open the Statistics screen before missing days are filled.
        def _refresh_stats_background():
            try:
                mgr = StatsManager(DATA_DIR)
                mgr.fill_missing_last_30_days(compute_day_from_remote)
                print("### STATS BACKGROUND REFRESH OK ###")
            except Exception as e:
                print("Stats background refresh error:", e)

        threading.Thread(target=_refresh_stats_background, daemon=True).start()

        # Initialize ad policy (event-based interstitial gating)
        try:
            self.ads = AdsPolicy(self)
            # Ensure session start is marked (first_open_ts)
            self.ads.touch_session_start(force=True)
        except Exception as e:
            print("AdsPolicy init error:", e)

        # Banner ads must be initialized after the Activity is ready.
        if not IS_ANDROID:
            return
        try:
            from jnius import autoclass
            from kivy.clock import Clock
        except Exception:
            return

        def _try_prepare_ads(*_):
            try:
                cfg = load_remote_config()
                if not remote_ads_enabled(cfg):
                    print("### ADS PREPARE SKIPPED ### remote_config disabled")
                    return

                AdBridge = autoclass('org.winalize.enigmax.AdBridge')

                # Unity / alternatif video ağı hazırlığı. Java tarafında hangi loader varsa güvenli dener.
                if remote_unity_enabled(cfg):
                    for method_name in ("loadUnityInterstitial", "loadUnityRewarded", "loadRewarded"):
                        _bridge_call(AdBridge, method_name, None)

                # AdMob yalnızca backup aktifse hazırlanır.
                if remote_admob_enabled(cfg):
                    _bridge_call(AdBridge, "loadInterstitial", None)

                # Banner sadece remote_config izin verirse hazırlanır ve eski stabil düzen gibi
                # ekranın altında sabit gösterilir. Maç kartı içi inline slotlar kaldırıldı.
                if remote_banner_enabled(cfg):
                    _bridge_call(AdBridge, "loadBanner", None)
                    _bridge_call(AdBridge, "showBanner", None)

                print("### ADS PREPARED ###", {
                    "ap": remote_master_ads_enabled(cfg),
                    "unity": remote_unity_enabled(cfg),
                    "admob": remote_admob_enabled(cfg),
                    "banner": remote_banner_enabled(cfg),
                    "mv": remote_int(cfg, "a", "mv", ADS_DAILY_MAX),
                    "vi": remote_int(cfg, "a", "vi", 15),
                })
            except Exception as e:
                print("AdBridge init error:", e)

        # Give Android a moment to finish wiring PythonActivity.mActivity
        Clock.schedule_once(_try_prepare_ads, 2.0)

    def reload_main(self):
        lang = self.get_pref("lang", DEFAULT_LANG)
        tz = self.get_pref("tz", DEFAULT_TZ)
        try:
            self.root.remove_widget(self.root.get_screen("main"))
        except Exception:
            pass
        m = Main(name="main")
        m.lang = lang
        m.tz_off = tz
        m._update_flag_and_tz()
        self.root.add_widget(m)
        self.root.current = "main"

    def on_stop(self):
        try:
            TRANSLATOR.save()
        except Exception as e:
            print("Translator save on_stop error:", e)

    def on_pause(self):
        if IS_ANDROID:
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                AppKiller = autoclass("org.winalize.enigmax.AppKiller")
                AppKiller.scheduleKill(activity, 60)  # 60 sn
            except Exception as e:
                print("scheduleKill error:", e)
        return True  # KRİTİK

    def on_resume(self):
        if IS_ANDROID:
            try:
                AppKiller = autoclass("org.winalize.enigmax.AppKiller")
                AppKiller.cancel()
            except Exception:
                pass



# === DISCLAIMER GATE (KIVY HYBRID) ===


# === LANGUAGE PREF HELPERS ===
def save_app_language(lang):
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        prefs = activity.getSharedPreferences("enigmax_prefs", 0)
        prefs.edit().putString("app_language", lang).apply()
    except Exception:
        pass

def load_app_language():
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        prefs = activity.getSharedPreferences("enigmax_prefs", 0)
        return prefs.getString("app_language", "")
    except Exception:
        return ""



if __name__ == "__main__":
    EnigmaxApp().run()

from kivy.utils import platform
from jnius import autoclass

def get_app_version():
    if platform == "android":
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            pm = activity.getPackageManager()
            package_info = pm.getPackageInfo(activity.getPackageName(), 0)
            return package_info.versionName
        except:
            return "Unknown"
    return "Desktop"


