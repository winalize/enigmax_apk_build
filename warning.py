import json
import os
import requests
from datetime import datetime, timedelta

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.animation import Animation

POPUP_PATH = os.path.join("data", "popup.json")
WARNING_PATH = os.path.join("data", "warning.json")

TARGET_TOKENS = [
    '[22,"UEFA Şampiyonlar Ligi"',
    '[203,"UEFA Avrupa Ligi"',
    '[611,"Dünya Kupası 2026 Elemeler"',
    '[646,"Dünya Kupası 2026"'
]

# 🏆 Dünya Kupası aktif tarih aralığı
WORLD_CUP_START = datetime(2026, 6, 10).date()
WORLD_CUP_END   = datetime(2026, 7, 20).date()

WINDOW_DAYS = 10
DATE_FMT = "%d/%m/%Y"

def today_date():
    return datetime.now().date()

def date_str(d):
    return d.strftime(DATE_FMT)

def parse_date(s):
    return datetime.strptime(s, DATE_FMT).date()

def read_warning_state():
    if not os.path.exists(WARNING_PATH):
        return "", []
    try:
        with open(WARNING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_check", ""), data.get("dates", [])
    except Exception:
        return "", []

def write_warning_state(last_check, dates):
    try:
        with open(WARNING_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"last_check": last_check, "dates": sorted(set(dates))},
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception:
        pass

def cleanup_dates(dates):
    today = today_date()
    valid = []
    for d in dates:
        try:
            dt = parse_date(d)
            if today <= dt <= today + timedelta(days=WINDOW_DAYS):
                valid.append(d)
        except Exception:
            pass
    return valid

def scan_specific_days(days):
    found = []
    for day in days:
        url = f"https://vd.mackolik.com/livedata?date={date_str(day)}"
        try:
            r = requests.get(url, timeout=6)
            if r.status_code != 200:
                continue
            text = r.text
            if any(tok in text for tok in TARGET_TOKENS):
                found.append(date_str(day))
        except Exception:
            continue
    return found

def update_warning_data():
    today = today_date()
    today_s = date_str(today)

    last_check, dates = read_warning_state()
    dates = cleanup_dates(dates)

    if last_check == today_s:
        write_warning_state(last_check, dates)
        return

    target_days = [today + timedelta(days=i) for i in range(WINDOW_DAYS + 1)]
    existing = set()
    for d in dates:
        try:
            existing.add(parse_date(d))
        except Exception:
            pass

    missing_days = [d for d in target_days if d not in existing]
    new_dates = scan_specific_days(missing_days)

    dates.extend(new_dates)
    write_warning_state(today_s, dates)

def get_warning_level():
    _, dates = read_warning_state()
    today = today_date()

    red_limit = today + timedelta(days=5)
    orange_limit = today + timedelta(days=10)

    # 🏆 Dünya Kupası dönemi
    if WORLD_CUP_START <= today <= WORLD_CUP_END:
        return "worldcup"

    for d in dates:
        try:
            if today <= parse_date(d) <= red_limit:
                return "red"
        except Exception:
            pass

    for d in dates:
        try:
            if today <= parse_date(d) <= orange_limit:
                return "orange"
        except Exception:
            pass

    return "green"

# 🔥 GLOW EFFECT
def attach_glow_effect(main):

    if not hasattr(main, "warning_icon"):
        return

    # Zaten ekliyse tekrar ekleme
    if hasattr(main, "warning_glow"):
        return

    parent = main.warning_icon.parent
    if not parent:
        return

    container = RelativeLayout(
        size=main.warning_icon.size,
        size_hint=main.warning_icon.size_hint
    )

    glow = Image(
        source="data/glow_white.png",
        size_hint=(None, None),
        size=(dp(72), dp(72)),
        pos_hint={"center_x": .5, "center_y": .5},
        opacity=1
    )

    main.warning_icon.pos_hint = {"center_x": .5, "center_y": .5}

    parent.remove_widget(main.warning_icon)
    container.add_widget(glow)
    container.add_widget(main.warning_icon)
    parent.add_widget(container)

    main.warning_glow = glow

    # ⚪ Pulse animasyon
    anim = Animation(opacity=0.35, duration=1.2) + \
           Animation(opacity=1.0, duration=1.2)
    anim.repeat = True
    anim.start(glow)

def update_warning_icon(main):
    update_warning_data()
    level = get_warning_level()
    main.warning_level = level

    icons = {
        "green": "data/yesil.png",
        "orange": "data/turuncu.png",
        "red": "data/kirmizi.png",
        "worldcup": "data/dk2026.png"
    }

    if hasattr(main, "warning_icon"):
        main.warning_icon.source = icons[level]

    attach_glow_effect(main)

def get_app_lang():
    app = App.get_running_app()
    try:
        return app.get_pref("lang", "en")
    except Exception:
        return "en"

def load_popup_text(lang, level):
    try:
        with open(POPUP_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if lang not in data:
            lang = "en"
        if level not in data[lang]:
            level = "green"
        return data[lang][level]["title"], data[lang][level]["body"]
    except Exception:
        return "Warning", ""

def on_warning_click(main):
    level = getattr(main, "warning_level", get_warning_level())
    lang = get_app_lang()
    title, body = load_popup_text(lang, level)
    WarningPopup(title, body, level).open()

class WarningPopup(ModalView):
    def __init__(self, title_text, body_text, level, **kw):
        self.size_hint = (0.65, 0.50)
        super().__init__(**kw)

        self.auto_dismiss = False
        pad = dp(16)

        icon_map = {
            "green": "data/yesil.png",
            "orange": "data/turuncu.png",
            "red": "data/kirmizi.png",
            "worldcup": "data/dk2026.png"
        }

        root = BoxLayout(
            orientation="vertical",
            padding=pad,
            spacing=dp(10)
        )

        if level in icon_map:
            icon = Image(
                source=icon_map[level],
                size_hint=(1, 0.4),
                allow_stretch=True,
                keep_ratio=True
            )
            root.add_widget(icon)

        title = Label(
            text=title_text,
            bold=True,
            font_size="16sp",
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(32)
        )
        title.bind(size=lambda *_: setattr(title, "text_size", (title.width, None)))

        body = Label(
            text=body_text,
            font_size="14sp",
            halign="center",
            valign="middle"
        )

        def sync_body(*_):
            body.text_size = (root.width - 2 * pad, None)
            body.texture_update()
            body.height = body.texture_size[1] + dp(8)

        root.bind(size=sync_body)
        Clock.schedule_once(lambda dt: sync_body(), 0)

        close_btn = Button(
            text="( X )",
            size_hint=(1, 0.18)
        )
        close_btn.bind(on_release=lambda *_: self.dismiss())

        root.add_widget(title)
        root.add_widget(body)
        root.add_widget(close_btn)

        self.add_widget(root)

    def on_open(self):
        self.center = Window.center