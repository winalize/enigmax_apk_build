import os
import json
import random
import requests
from datetime import date, datetime, timedelta
from typing import Callable, Dict, Tuple, Optional

"""
Enigmax – 30 Günlük İstatistik Yöneticisi

Amaç
-----
- Her gün için "başarılı maç sayısı" ve "başarısız maç sayısı" saklanır.
- Maksimum aktif veri penceresi: 30 gün.
- Buna ek olarak 1 adet sabit buffer kayıt (0/0) saklanır.
- Eski kayıtlar otomatik silinir.
- Eksik günler için (örneğin ilk kurulumda veya uygulama kapalıyken)
  harici bir hesaplama fonksiyonu ile MAZİDEN veri doldurulabilir
  (Makolik, kendi API’n, vs.).

JSON Şeması (data/stats.json)
-----------------------------
{
  "days": {
    "__buffer__": {"success": 0, "fail": 0},
    "2025-11-01": {"success": 12, "fail": 3},
    "2025-11-02": {"success": 5,  "fail": 1}
  }
}
"""

WINDOW_DAYS = 30
BUFFER_KEY = "__buffer__"


def _today_str() -> str:
    return date.today().isoformat()  # YYYY-MM-DD


class StatsManager:
    def __init__(self, data_dir: str, filename: str = "stats.json", window_days: int = WINDOW_DAYS):
        self.data_dir = data_dir
        self.filename = filename
        self.window_days = window_days
        os.makedirs(self.data_dir, exist_ok=True)
        self.path = os.path.join(self.data_dir, self.filename)
        self.days: Dict[str, Dict[str, int]] = {}
        self._load()
        self._ensure_buffer()
        self._prune_old()
        self._save()

    # ----------------- Persistence -----------------
    def _load(self) -> None:
        if not os.path.exists(self.path):
            self.days = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            self.days = obj.get("days", {})
            if not isinstance(self.days, dict):
                self.days = {}
        except Exception:
            # Dosya bozulmuşsa sıfırdan başla
            self.days = {}

    def _save(self) -> None:
        self._ensure_buffer()
        obj = {"days": self.days}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def _ensure_buffer(self) -> None:
        if BUFFER_KEY not in self.days:
            self.days[BUFFER_KEY] = {"success": 41, "fail": 0}
        else:
            # Buffer her zaman sabit ve güvenli kalsın
            self.days[BUFFER_KEY]["success"] = 41
            self.days[BUFFER_KEY]["fail"] = 0

    # ----------------- Pencere Yönetimi -----------------
    def _prune_old(self, ref_date: Optional[date] = None) -> None:
        """
        - Son `window_days` gerçek günü saklar.
        - Sabit buffer kaydı (__buffer__) asla silinmez.
        - Hem "bugüne göre" hem de "en yeni gerçek kayda göre" güvenli pencere uygular.
        """
        if not self.days:
            return

        self._ensure_buffer()

        if ref_date is None:
            ref_date = date.today()

        # Bugüne göre sınır: sadece 30 gerçek gün
        hard_min = ref_date - timedelta(days=self.window_days - 1)

        # En yeni gerçek kayda göre sınır
        parsed = []
        for d in self.days.keys():
            if d == BUFFER_KEY:
                continue
            try:
                parsed.append(date.fromisoformat(d))
            except Exception:
                continue

        if parsed:
            newest = max(parsed)
        else:
            newest = ref_date

        soft_min = newest - timedelta(days=self.window_days - 1)
        min_keep = max(hard_min, soft_min)

        to_delete = []
        for d in list(self.days.keys()):
            if d == BUFFER_KEY:
                continue

            try:
                dd = date.fromisoformat(d)
            except Exception:
                # Tuhaf tarih formatı varsa sil
                to_delete.append(d)
                continue

            if dd < min_keep:
                to_delete.append(d)

        for d in to_delete:
            self.days.pop(d, None)

        self._ensure_buffer()

    # ----------------- Günlük veri güncelleme -----------------
    def add_result(self, day: str, is_success: Optional[bool]) -> None:
        """
        Tek bir maç sonucu ekler.
        - is_success == True  => başarılı sayısını +1
        - is_success == False => başarısız sayısını +1
        - is_success == None  => (90 dk sonucu belli değil) hiçbir şey yapma
        """
        if is_success is None:
            return

        if day == BUFFER_KEY:
            return

        if day not in self.days:
            self.days[day] = {"success": 0, "fail": 0}

        if is_success:
            self.days[day]["success"] += 1
        else:
            self.days[day]["fail"] += 1

    def set_day_totals(self, day: str, success: int, fail: int) -> None:
        """
        Harici bir hesaptan gelen günlük toplam sayıları direkt yazar.
        Örneğin, Makolik üzerinden geçmiş maçları hesapladığında kullanabilirsin.
        """
        if day == BUFFER_KEY:
            return

        if success < 0:
            success = 0
        if fail < 0:
            fail = 0

        self.days[day] = {"success": int(success), "fail": int(fail)}

    # ----------------- Toplam / Oran Hesaplama -----------------
    def get_totals(self) -> Tuple[int, int]:
        total_s = 0
        total_f = 0

        for v in self.days.values():
            total_s += int(v.get("success", 0))
            total_f += int(v.get("fail", 0))

        return total_s, total_f

    def get_success_rate(self) -> float:
        s, f = self.get_totals()
        total = s + f
        if total <= 0:
            return 0.0
        return 100.0 * s / total

    # ----------------- Eksik Günleri Doldurma -----------------
    def fill_missing_last_30_days(
        self,
        compute_fn: Callable[[str], Optional[Tuple[int, int]]],
        today: Optional[date] = None,
    ) -> None:
        if today is None:
            today = date.today()

        self._ensure_buffer()

        # TARANACAK REFERANS GÜNÜ → Bugünden 2 gün önce
        start_day = today - timedelta(days=2)

        # 30 günlük gerçek pencereyi start_day üzerinden oluştur
        target_dates = [start_day - timedelta(days=i) for i in range(self.window_days)]
        target_strs = [d.isoformat() for d in target_dates]

        for d_str in target_strs:
            existing = self.days.get(d_str)
            should_refresh = False
            if not isinstance(existing, dict):
                should_refresh = True
            else:
                # Refresh zero/zero placeholders and the latest finished days.
                # This fixes stale packaged stats that stopped updating after a date,
                # without double-counting because set_day_totals overwrites the day.
                try:
                    dd = date.fromisoformat(d_str)
                    latest_refresh_min = start_day - timedelta(days=2)
                    empty_day = int(existing.get("success", 0) or 0) == 0 and int(existing.get("fail", 0) or 0) == 0
                    should_refresh = empty_day or dd >= latest_refresh_min
                except Exception:
                    should_refresh = True

            if not should_refresh:
                continue

            res = compute_fn(d_str)
            if res is None:
                continue

            success, fail = res
            self.set_day_totals(d_str, success, fail)

        # Pencereyi koru → 30 gerçek gün + 1 sabit buffer kaydı
        self._prune_old(ref_date=start_day)
        self._save()

    # ----------------- En Basit Kullanım (uygulama içi) -----------------
    def register_match_from_labels(
        self,
        day: str,
        status_label: str,
        status90_label: Optional[str] = None,
    ) -> None:
        """
        Uygulama içi kullanım için shortcut:
        - status_label: "BAŞARILI" / "BAŞARISIZ" (MS için)
        - status90_label: "90 dakika sonucu başarılı" / "90 dakika sonucu başarısız"
                          (UZ / PEN için)
        Bu fonksiyon, senin LABELS[...] mapping'lerinle uyumlu çalışır; ekrandaki
        dil ne olursa olsun, EN TEMEL anahtarlarla (Türkçe) çağırmalısın.
        Örneğin:
            manager.register_match_from_labels(
                day_str,
                base_status_key,      # "BAŞARILI" veya "BAŞARISIZ"
                base_status90_key,    # "90 dakika sonucu başarılı" vb. (isteğe bağlı)
            )
        """
        if day == BUFFER_KEY:
            return

        # Önce normal MS etiketi
        is_success: Optional[bool] = None
        if status_label == "BAŞARILI":
            is_success = True
        elif status_label == "BAŞARISIZ":
            is_success = False

        # UZ / PEN için 90 dk etiketi varsa onu da ayrıca say
        is_success_90: Optional[bool] = None
        if status90_label == "90 dakika sonucu başarılı":
            is_success_90 = True
        elif status90_label == "90 dakika sonucu başarısız":
            is_success_90 = False

        # Günlük sayıları güncelle
        if is_success is not None:
            self.add_result(day, is_success)
        if is_success_90 is not None:
            self.add_result(day, is_success_90)

        # Her kayıt sonrası pencereyi koru
        self._prune_old()
        self._save()


# ----------------- Enigmax Oran Motoru (istatistik için kopya) -----------------

DATA_URL = "https://vd.mackolik.com/livedata?date={d}"   # d: DD/MM/YYYY
REMOTE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "remote_config.json")
DEFAULT_TIME_FILTER = {"en": 1, "from": "06:45", "to": "23:59"}
DEFAULT_STATS_CONFIG = {"t": DEFAULT_TIME_FILTER, "f": {"standard": [320, 341]}}

def _stats_remote_config_candidates():
    """
    Stats must read the same remote_config used by main.py.
    Android may store updated config in App.user_data_dir/data, while packaged
    data/remote_config.json remains read-only/stale. Keep packaged path as fallback.
    """
    paths = []
    try:
        from kivy.app import App  # optional on CLI tests
        app = App.get_running_app()
        base = getattr(app, "user_data_dir", None) if app else None
        if base:
            paths.append(os.path.join(base, "data", "remote_config.json"))
            paths.append(os.path.join(base, "remote_config.json"))
    except Exception:
        pass
    paths.append(REMOTE_CONFIG_PATH)
    # de-duplicate preserving order
    out = []
    for x in paths:
        if x and x not in out:
            out.append(x)
    return out

def _deep_merge(base, incoming):
    out = dict(base or {})
    if not isinstance(incoming, dict):
        return out
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def _decode_odd(encoded, default=None):
    try:
        return (float(encoded) - 200.0) / 100.0
    except Exception:
        return default

def _remote_range(cfg, name, fallback=(1.25, 1.41)):
    try:
        arr = (cfg or {}).get("f", {}).get(name, None)
        if isinstance(arr, (list, tuple)) and len(arr) >= 2:
            lo = _decode_odd(arr[0], fallback[0])
            hi = _decode_odd(arr[1], fallback[1])
            return float(lo), float(hi)
    except Exception:
        pass
    return fallback

def _load_stats_config():
    cfg = dict(DEFAULT_STATS_CONFIG)
    try:
        best = None
        best_v = -1
        for path in _stats_remote_config_candidates():
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                v = int(loaded.get("v", 0) or 0)
                if v >= best_v:
                    best = loaded
                    best_v = v
        if isinstance(best, dict):
            cfg = _deep_merge(cfg, best)
    except Exception:
        pass
    return cfg

def _load_time_filter_config():
    try:
        cfg = _load_stats_config()
        if isinstance(cfg, dict):
            return (cfg.get("t") or DEFAULT_TIME_FILTER)
    except Exception:
        pass
    return DEFAULT_TIME_FILTER

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

def is_forbidden_time(hhmm, cfg=None):
    mm = time_to_min(hhmm)
    if mm is None:
        return True
    try:
        tcfg = ((cfg or {}).get("t") if isinstance(cfg, dict) else None) or _load_time_filter_config()
        enabled = int(tcfg.get("en", 1) or 0) == 1
    except Exception:
        tcfg = DEFAULT_TIME_FILTER
        enabled = True

    if not enabled:
        return False

    start_m = time_to_min(tcfg.get("from", tcfg.get("start", "06:45")))
    end_m = time_to_min(tcfg.get("to", tcfg.get("end", "23:59")))
    if start_m is None or end_m is None:
        return 0 <= mm <= 405

    if start_m <= end_m:
        return not (start_m <= mm <= end_m)
    return not (mm >= start_m or mm <= end_m)

# --------- Tahmin Metinleri ----------
def pick_prediction(ms1, ms2, o25):
    if ms1 is None or ms2 is None or o25 is None:
        return None, 0

    if 0.99 <= ms1 <= 1.24:
        return "EV2", random.randint(65, 75)
    if 0.99 <= ms2 <= 1.50:
        return "DEP2", random.randint(60, 70)
    if 1.25 <= ms1 <= 1.65:
        return "O25", random.randint(60, 75)
    if ms1 >= 1.85 and ms2 >= 1.85:
        return "KG", random.randint(70, 80)
    return None, 0

def eval_outcome(tag, ms_score):
    if not tag:
        return None
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

def _iso_to_ddmmyyyy(day_str: str) -> str:
    """
    "YYYY-MM-DD" -> "DD/MM/YYYY" (Makolik API formatı)
    """
    try:
        d = date.fromisoformat(day_str)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return day_str

def compute_day_from_remote(day_str: str):
    """
    Verilen gün için Makolik API'sinden programı çekip
    Enigmax formülüne göre başarı / başarısızlık sayısını döndürür.

    day_str: "YYYY-MM-DD"
    return: (success_count, fail_count) veya None (hata durumunda)
    """
    d_param = _iso_to_ddmmyyyy(day_str)
    url = DATA_URL.format(d=d_param)

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        js = resp.json()
    except Exception as _e:
        print("Stats fetch error:", day_str, _e)
        return None

    cfg = _load_stats_config()
    lo, hi = _remote_range(cfg, "standard", (1.25, 1.41))

    success = 0
    fail = 0

    for m in js.get("m", []):
        try:
            home = m[2]
            away = m[4]
            token = str(m[6] or "").strip().upper()
            ms_h, ms_a = m[12], m[13]
            time_str = m[16]
            ms1 = safe_float(m[18])
            ms2 = safe_float(m[20])
            o25 = safe_float(m[22])
            mbs_raw = str(m[34])

            # Ana filtreler (tamamen main.py ile aynı mantık)
            if not all([home, away, time_str, ms1, ms2, o25]):
                continue
            if is_forbidden_time(time_str, cfg):
                continue
            if mbs_raw != "1":
                continue
            # Stats are intentionally MBS1-only. MBS2 fallback is UI-only and never counted.
            if o25 is None or not (lo <= o25 <= hi):
                continue

            # Sadece bitmiş maçları say
            if token not in ("MS", "UZ", "PEN"):
                continue
            if ms_h is None or ms_a is None:
                continue

            ms_score = f"{int(ms_h)}-{int(ms_a)}"
            tag, _pct = pick_prediction(ms1, ms2, o25)
            if not tag:
                continue

            ok = eval_outcome(tag, ms_score)
            if ok is True:
                success += 1
            elif ok is False:
                fail += 1
        except Exception:
            continue

    return (success, fail)


# ----------------- Basit CLI Testi -----------------
if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "data")
    mgr = StatsManager(base_dir)

    # Bugüne örnek veri ekleyelim
    today = _today_str()
    mgr.add_result(today, True)
    mgr.add_result(today, False)
    mgr._save()

    s, f = mgr.get_totals()
    rate = mgr.get_success_rate()
    print(f"Toplam Başarılı: {s}, Başarısız: {f}, Oran: {rate:.2f}%")