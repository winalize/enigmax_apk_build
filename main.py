# -- coding: utf-8 --
# 🎯 Winalize Sports – Enigmax GUI v6.0 (UEFA Tema, Neon T/D)
# - Arka plan: icon_bg.png (1080x1920 gibi yüksek çöz. dikey görsel önerilir)
# - Üst bar daraltıldı; saat "pill" çerçevesi metne göre otomatik
# - T (Tüm) / D (Devam) neon butonlar; aktif olan parlak halka (0.1 min width)
# - Gün butonları: Dün / Bugün / Yarın
# - Kartlar: Logobox büyütüldü; logo kenara değmiyor
# - Detaylar: Tahmin satırı ALTIN rengi (kalsın)
# - ScrollView tabanda tampon: Databox telefon tuşlarının altında kalmıyor
# - Liste yenilenince üste kaydırma
# - Filtreler KORUNDU:
#     * Sabit indeks ayrıştırma
#     * O25 oranı 1.25–1.41 (dahil)
#     * MBS 1–2
#     * 00:00–06:45 dışı
#     * UZ / PEN maçları hariç
#     * D modu: sadece "", "IY" veya dakika (sayısal) token'lı maçlar

import datetime, random, requests
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.image import AsyncImage, Image
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.animation import Animation

# ---------- Tema ----------
Window.clearcolor = (0.03, 0.03, 0.05, 1)
TEXT        = (1, 1, 1, 1)
GREEN       = (0.20, 0.92, 0.25, 1)   # BAŞARILI
RED         = (1.00, 0.35, 0.35, 1)   # BAŞARISIZ
YELLOW      = (1.00, 0.84, 0.00, 1)   # DK DEVAM / IY
BLUE_SOFT   = (0.75, 0.85, 1.00, 1)   # HENÜZ BAŞLAMADI
ORANGE      = (1.00, 0.60, 0.20, 1)   # ERT / YRDK
CARD        = (1, 1, 1, 0.06)
LIGHT_BLUE  = (0.10, 0.25, 0.55, 0.35) # logobox bg
GOLD        = (1.00, 0.86, 0.25, 1)    # tahmin satırı

NEON_FUCHSIA= (0.90, 0.35, 1.00, 1)    # T buton ana renk
NEON_TEAL   = (0.25, 1.00, 0.95, 1)    # D buton ana renk
NEON_RING   = (0.20, 0.85, 1.00, 0.90)

FONT_BIG, FONT_MED, FONT_SM = "18sp", "16sp", "14sp"

BG_PATH = r"C:\Users\aCER\Desktop\tema\icon_bg.png"

# ---------- Yardımcı ----------
def today_str(off=0):
    return (datetime.date.today() + datetime.timedelta(days=off)).strftime("%d/%m/%Y")

def build_url(datestr):
    return f"https://vd.mackolik.com/livedata?date={datestr}"

def logo_url(team_id):
    return f"https://im.mackolik.com/img/logo/buyuk/{team_id}.gif"

def safe_float(v):
    try:
        f = float(str(v).replace(",", "."))
        if 1.01 <= f <= 20.0:
            return f
    except:
        pass
    return None

def time_to_min(hhmm):
    try:
        h, m = map(int, hhmm.split(":"))
        return h * 60 + m
    except:
        return None

def is_forbidden_time(hhmm):
    mm = time_to_min(hhmm)
    return (mm is None) or (0 <= mm <= 405)  # 00:00–06:45

# ---------- Tahmin ----------
def pick_prediction(ms1, ms2, o25):
    if 1.00 <= ms1 <= 1.24:
        return "EV2", "* Ev Sahibi 2+ gol atar *  %" + str(random.randint(65, 75))
    if 1.00 <= ms2 <= 1.50:
        return "DEP2","* Deplasman 2+ gol atar * %" + str(random.randint(60, 70))
    if 1.25 <= ms1 <= 1.80:
        return "O25","* En az 3 gol olur *   %" + str(random.randint(60, 75))
    if ms1 >= 1.85 and ms2 >= 1.85:
        return "KG",  "* Karşılıklı gol var *  %" + str(random.randint(70, 80))
    return "O25","* En az 3 gol olur *   %" + str(random.randint(60, 75))

def eval_outcome(tag, ms_score):
    if not ms_score or "-" not in ms_score:
        return None
    try:
        h, a = map(int, ms_score.split("-"))
        if tag == "EV2": return h >= 2
        if tag == "DEP2": return a >= 2
        if tag == "O25": return (h + a) >= 3
        if tag == "KG":  return (h > 0 and a > 0)
    except:
        pass
    return None

# ---------- Neon Toggle (T / D) ----------
class NeonToggle(ButtonBehavior, AnchorLayout):
    def __init__(self, text, base_color, on_press_cb=None, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (dp(44), dp(44))
        self._active = False
        self.base_color = base_color
        self.on_press_cb = on_press_cb

        # Çizimler
        with self.canvas.before:
            # arka yuvarlak
            Color(0, 0, 0, 0.45)
            self._bg = Ellipse(pos=self.pos, size=self.size)
            # iç parlak disk
            Color(*self.base_color)
            self._disk = Ellipse(pos=self.pos, size=(dp(44), dp(44)))
            # dış halka (aktifken kalın)
            Color(*NEON_RING)
            self._ring = Line(circle=(self.center_x, self.center_y, dp(24)), width=0.1)  # 0 değil!

        self.bind(pos=self.sync, size=self.sync)
        self.lbl = Label(text=text, color=(0,0,0,1), bold=True)
        self.add_widget(self.lbl)

    def sync(self, *_):
        s = min(self.width, self.height)
        self._bg.pos  = (self.center_x - s/2, self.center_y - s/2)
        self._bg.size = (s, s)
        self._disk.pos = (self.center_x - s/2, self.center_y - s/2)
        self._disk.size= (s, s)
        self._ring.circle = (self.center_x, self.center_y, s/2 + dp(2))

    def set_active(self, val: bool):
        self._active = bool(val)
        # aktifken yazı beyaz, disk parlak; halkayı kalın yap
        self.lbl.color = (1,1,1,1) if self._active else (0,0,0,1)
        self._ring.width = dp(3.2) if self._active else 0.1  # asla 0 yapma
        # hafif animasyon
        Animation.cancel_all(self._disk)
        Animation(size=(dp(46), dp(46)), d=0.10).start(self._disk) if self._active else Animation(size=(dp(44), dp(44)), d=0.10).start(self._disk)

    def on_release(self):
        if self.on_press_cb:
            self.on_press_cb(self)

# ---------- Saat "pill" ----------
class ClockPill(Label):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.font_size = FONT_BIG
        self.color = (0.85, 0.95, 1.0, 1)
        self.padding_h = dp(22)
        self.padding_v = dp(8)
        self.size_hint = (None, None)
        self.text = datetime.datetime.now().strftime("%H:%M:%S")
        self.texture_update()
        self._resize_to_text()

        with self.canvas.before:
            Color(0, 0, 0, 0.55)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[16])
            Color(0.12, 0.85, 1.0, 1)
            self._bd = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 16], width=1.3)

        self.bind(pos=self.sync, size=self.sync)
        Clock.schedule_interval(self.tick, 1)

    def _resize_to_text(self):
        w = self.texture_size[0] + self.padding_h*2
        h = self.texture_size[1] + self.padding_v*2
        self.size = (w, h)

    def tick(self, *_):
        self.text = datetime.datetime.now().strftime("%H:%M:%S")
        self.texture_update()
        self._resize_to_text()

    def sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._bd.rounded_rectangle = [self.x, self.y, self.width, self.height, 16]

# ---------- Gün Butonu ----------
class GlassButton(Button):
    def _init_(self, **kw):
        super()._init_(**kw)
        self.background_normal = ""
        self.background_color  = (0.08, 0.10, 0.18, 0.95)  # koyu mavi-siyah
        self.color = (1, 1, 1, 1)
        self.font_size = "16sp"
        self.size_hint_y = None
        self.height = dp(46)
        with self.canvas.before:
            Color(0.25, 0.60, 1.00, 0.15)  # kenarda hafif mavi parlama
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[14])
        self.bind(pos=self._sync, size=self._sync)

    def sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size

    def set_active(self, active):
        if active:
            # aktif buton: mavi vurgulu, açık yazı
            self.background_color = (0.15, 0.35, 0.80, 0.9)
            self.color = (1, 1, 1, 1)
        else:
            # pasif buton: koyu mavi arka plan
            self.background_color = (0.08, 0.10, 0.18, 0.95)
            self.color = (0.85, 0.9, 1, 1)
# ---------- Kart ----------
class HeaderButton(ButtonBehavior, BoxLayout):
    pass

class MatchCard(BoxLayout):
    def __init__(self, m, on_toggle_open=None, **kw):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), size_hint_y=None, **kw)
        self.on_toggle_open = on_toggle_open
        self.is_open = False

        self.h_logobox = dp(136)   # bir tık daha yüksek
        self.h_status  = dp(30)
        self.h_detail_open = dp(112)
        self.h_detail  = 0

        with self.canvas.before:
            Color(*CARD)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
        self.bind(pos=self.sync_bg, size=self.sync_bg)

        # --- Logobox ---
        self.logobox = HeaderButton(orientation="vertical", size_hint_y=None,
                                    height=self.h_logobox, padding=dp(8), spacing=dp(6))
        with self.logobox.canvas.before:
            Color(*LIGHT_BLUE)
            self._lb_bg = RoundedRectangle(pos=self.logobox.pos, size=self.logobox.size, radius=[12])
        self.logobox.bind(pos=self.sync_lb, size=self.sync_lb)
        self.logobox.bind(on_release=self.toggle)

        row = GridLayout(cols=3, spacing=dp(10), size_hint_y=None, height=self.h_logobox - dp(16))
        row.add_widget(self._logo_col(m["home_id"], m["home"]))
        # VS
        vsbox = AnchorLayout(anchor_x='center', anchor_y='center')
        with vsbox.canvas.before:
            Color(0, 0, 0, 1)
            self._vs_circle = Ellipse(size=(dp(58), dp(58)), pos=vsbox.pos)
        def sync_vs(*_):
            s = dp(58)
            self._vs_circle.size = (s, s)
            self._vs_circle.pos  = (vsbox.center_x - s/2, vsbox.center_y - s/2)
        vsbox.bind(pos=sync_vs, size=sync_vs)
        vsbox.add_widget(Label(text="VS", color=YELLOW, font_size="18sp"))
        row.add_widget(vsbox)
        row.add_widget(self._logo_col(m["away_id"], m["away"]))
        self.logobox.add_widget(row)
        self.add_widget(self.logobox)

        # --- Databox ---
        self.databox = BoxLayout(orientation="vertical", size_hint_y=None,
                                 height=self.h_status + self.h_detail, padding=dp(6), spacing=dp(4))
        with self.databox.canvas.before:
            Color(1, 1, 1, 0.04)
            self._db_bg = RoundedRectangle(pos=self.databox.pos, size=self.databox.size, radius=[12])
        self.databox.bind(pos=self.sync_db, size=self.sync_db)

        self.lbl_status = Label(text=m["status_text"], color=m["status_color"],
                                font_size=FONT_MED, size_hint_y=None, height=self.h_status)
        self.databox.add_widget(self.lbl_status)

        self.detail = BoxLayout(orientation="vertical", size_hint_y=None, height=self.h_detail, opacity=0)
        self.detail.add_widget(Label(text=f'{m["league"]} - {m["country"]}  |  {m["time"]}',
                                     color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(24)))
        # Tahmin satırı (ALTIN)
        self.detail.add_widget(Label(text=m["suggest"], color=GOLD, font_size=FONT_MED,
                                     size_hint_y=None, height=dp(28)))
        self.detail.add_widget(Label(text=f'İY: {m["iy"] or "-"}   |   MS: {m["ms_score"] or "-"}',
                                     color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(24)))
        self.databox.add_widget(self.detail)
        self.add_widget(self.databox)
        self._recalc_height()

    def _logo_col(self, team_id, name):
        col = BoxLayout(orientation="vertical", spacing=dp(6))
        # Logo sınır içinde dursun
        col.add_widget(AsyncImage(source=logo_url(team_id), size_hint_y=None,
                                  height=dp(78), allow_stretch=True, keep_ratio=True))
        name_lbl = Label(text=name, color=(0.9, 0.95, 1.0, 1), font_size="14sp",
                         size_hint_y=None, height=dp(40), halign="center", valign="middle")
        name_lbl.bind(size=lambda *_: setattr(name_lbl, "text_size", name_lbl.size))
        col.add_widget(name_lbl)
        return col

    # --- helpers ---
    def _recalc_height(self):
        self.height = self.h_logobox + (self.h_status + self.h_detail) + dp(10) + dp(8)
    def sync_bg(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size
    def sync_lb(self, *_):
        self._lb_bg.pos, self._lb_bg.size = self.logobox.pos, self.logobox.size
    def sync_db(self, *_):
        self._db_bg.pos, self._db_bg.size = self.databox.pos, self.databox.size

    def toggle(self, *_):
        if self.on_toggle_open:
            self.on_toggle_open(self)
        Animation.cancel_all(self.detail); Animation.cancel_all(self)
        if not self.is_open:
            anim = Animation(height=self.h_detail_open, opacity=1, d=0.20, t='out_cubic')
            anim.bind(on_progress=lambda *_: self._during())
            anim.start(self.detail)
            self.is_open = True
        else:
            anim = Animation(height=0, opacity=0, d=0.18, t='out_cubic')
            anim.bind(on_progress=lambda *_: self._during())
            anim.start(self.detail)
            self.is_open = False

    def _during(self):
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

# ---------- Ana Ekran ----------
class Main(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.selected_day = 0
        self.open_card = None
        self.show_mode = "T"  # T: tüm, D: canlı/erken token filtresi

        root_float = FloatLayout()  # arka plan için
        # BG image
        try:
            bg = Image(source=BG_PATH, allow_stretch=True, keep_ratio=False, size_hint=(1,1), pos=(0,0))
            root_float.add_widget(bg)
        except:
            pass

        # Ön plan dikey düzen
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        root_float.add_widget(root)

        # Üst bar (dar)
        top = GridLayout(cols=3, size_hint_y=None, height=dp(72))
        # Sol: tarih + T/D
        left = BoxLayout(orientation="vertical", spacing=dp(6))
        self.lbl_date = Label(text=today_str(0), color=(0.85,0.95,1,1), font_size=FONT_BIG,
                              size_hint_y=None, height=dp(28))
        left.add_widget(self.lbl_date)
        tdrow = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(44))
        self.btn_T = NeonToggle(text="T", base_color=NEON_FUCHSIA, on_press_cb=self._on_td_pressed)
        self.btn_D = NeonToggle(text="D", base_color=NEON_TEAL,    on_press_cb=self._on_td_pressed)
        self.btn_T.set_active(True)  # başlangıç: T
        tdrow.add_widget(self.btn_T); tdrow.add_widget(self.btn_D)
        left.add_widget(tdrow)
        top.add_widget(left)

        # Orta: saat
        center = AnchorLayout(anchor_x='center', anchor_y='center')
        self.lbl_clock = ClockPill()
        center.add_widget(self.lbl_clock)
        top.add_widget(center)

        # Sağ: başarı %
        right = AnchorLayout(anchor_x='center', anchor_y='center')
        self.lbl_success = Label(text="Başarı: %--", color=GREEN, font_size=FONT_BIG)
        right.add_widget(self.lbl_success)
        top.add_widget(right)
        root.add_widget(top)

        # Gün butonları
        days = GridLayout(cols=3, size_hint_y=None, height=dp(50), spacing=dp(8))
        self.btn_dun   = GlassButton(text="Dün",   on_release=lambda *_: self._set_day(-1))
        self.btn_bugun = GlassButton(text="Bugün", on_release=lambda *_: self._set_day(0))
        self.btn_yarin = GlassButton(text="Yarın", on_release=lambda *_: self._set_day(1))
        days.add_widget(self.btn_dun); days.add_widget(self.btn_bugun); days.add_widget(self.btn_yarin)
        root.add_widget(days)
        self.day_buttons = [self.btn_dun, self.btn_bugun, self.btn_yarin]
        self._update_day_buttons()

        # Liste
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=[0,0,0,dp(6)])
        self.list_box.bind(minimum_height=lambda _, h: setattr(self.list_box, "height", h))
        self.scroll = ScrollView()
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)

        self.add_widget(root_float)
        Clock.schedule_once(lambda *_: self.load_and_render(), 0.2)

    # ----- TD -----
    def _on_td_pressed(self, who: NeonToggle):
        # tek seçim
        if who is self.btn_T:
            self.btn_T.set_active(True)
            self.btn_D.set_active(False)
            self.show_mode = "T"
        else:
            self.btn_T.set_active(False)
            self.btn_D.set_active(True)
            self.show_mode = "D"
        self.load_and_render()

    # ----- Gün -----
    def _update_day_buttons(self):
        for i, b in enumerate(self.day_buttons):
            b.set_active(i-1 == self.selected_day)

    def _set_day(self, off):
        self.selected_day = off
        self.lbl_date.text = today_str(off)
        self._update_day_buttons()
        self.load_and_render()

    # ----- Status -----
    def _status_from_token(self, token, tag, ms_score):
        t = str(token).strip().upper()
        if t in ("UZ", "PEN"):   # zaten listeden çıkarıyoruz ama kalırsa da:
            return ("", TEXT)
        if t == "ERT":  return ("ERTELENDİ", ORANGE)
        if t == "YRDK": return ("YARIDA KALDI", ORANGE)
        if t == "MS":
            ok = eval_outcome(tag, ms_score)
            if ok is True:  return ("BAŞARILI", GREEN)
            if ok is False: return ("BAŞARISIZ", RED)
            return ("MAÇ TAMAMLANDI", TEXT)
        if t == "IY":   return ("DEVRE ARASI", YELLOW)
        if t.isdigit(): return (f"{t}. DK DEVAM EDİYOR", YELLOW)
        return ("HENÜZ BAŞLAMADI", BLUE_SOFT)

    # ----- Data -----
    def load_and_render(self):
        self.list_box.clear_widgets()
        # üstte boşluk (uygun maç bulunamadı mesajı için)
        spacer_top = Widget(size_hint_y=None, height=dp(4))
        self.list_box.add_widget(spacer_top)

        d = today_str(self.selected_day)
        info = Label(text=f"{d} için veriler çekiliyor...", color=TEXT, font_size=FONT_SM, size_hint_y=None, height=dp(28))
        self.list_box.add_widget(info)

        rows = []
        try:
            js = requests.get(build_url(d), timeout=15).json()
        except Exception as e:
            info.text = f"Hata: {e}"
            return

        for m in js.get("m", []):
            try:
                # ------- Sabit indeksler -------
                home_id, home = m[1], m[2]
                away_id, away = m[3], m[4]
                token = m[6]
                iy = m[7]
                ms_h, ms_a = m[12], m[13]
                time_str = m[16]
                ms1, ms2, o25 = safe_float(m[18]), safe_float(m[20]), safe_float(m[22])
                mbs_raw = str(m[34])
                lgblk = m[36] if isinstance(m[36], list) else ["", "", "", ""]
                country = lgblk[1] if len(lgblk) > 1 else ""
                league  = lgblk[3] if len(lgblk) > 3 else ""

                # ------- Filtreler -------
                if not all([home, away, time_str, ms1, ms2, o25]):
                    continue
                if is_forbidden_time(time_str):
                    continue
                if mbs_raw not in ("1", "2"):
                    continue
                # Ana filtre: O25 oranı 1.25–1.41 (dahil)
                if o25 is None or not (1.25 <= o25 <= 1.41):
                    continue
                # UZ / PEN hariç
                if str(token).strip().upper() in ("UZ", "PEN"):
                    continue
                # D modu: sadece "", "IY" veya dakika
                if self.show_mode == "D":
                    tt = str(token).strip().upper()
                    if not (tt == "" or tt == "IY" or tt.isdigit()):
                        continue

                ms_score = f"{ms_h}-{ms_a}" if (ms_h is not None and ms_a is not None) else ""
                tag, suggest = pick_prediction(ms1, ms2, o25)
                stxt, scol = self._status_from_token(token, tag, ms_score)

                rows.append(dict(
                    home=home, away=away, home_id=home_id, away_id=away_id,
                    league=league, country=country, time=time_str,
                    iy=iy, ms_score=ms_score, suggest=suggest,
                    status_text=stxt, status_color=scol
                ))
            except:
                continue

        # Saat sırasına göre sırala
        rows.sort(key=lambda x: (time_to_min(x["time"]) if time_to_min(x["time"]) is not None else 99999))

        # Başarı %
        succ = sum(1 for r in rows if r["status_text"].startswith("BAŞARILI"))
        fin  = sum(1 for r in rows if any(r["status_text"].startswith(x) for x in ("BAŞARILI","BAŞARISIZ","MAÇ TAM")))
        self.lbl_success.text = f"Başarı: %{(succ / max(1, fin) * 100):.1f}" if fin else "Başarı: %--"

        # Listeyi bas
        self.list_box.clear_widgets()
        if not rows:
            # mesaj altta kalmasın diye ekstra boşluk
            self.list_box.add_widget(Widget(size_hint_y=None, height=dp(12)))
            self.list_box.add_widget(Label(text="Uygun maç bulunamadı.", color=TEXT, font_size=FONT_MED,
                                           size_hint_y=None, height=dp(36)))
            self.list_box.add_widget(Widget(size_hint_y=None, height=dp(120)))  # nav bar tamponu
            self.scroll.scroll_y = 1.0
            return

        for m in rows:
            card = MatchCard(m, on_toggle_open=self._set_open_card)
            self.list_box.add_widget(card)

        # tabanda tampon bırak (telefon alt tuşlar kapatmasın)
        self.list_box.add_widget(Widget(size_hint_y=None, height=dp(120)))
        # her yenilemede başa al
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 1.0), 0.05)

    def _set_open_card(self, card):
        if self.open_card and self.open_card is not card:
            self.open_card.force_close()
        self.open_card = card

# ---------- App ----------
class EnigmaxApp(App):
    title = "Winalize"

    def build(self):
        self.root = FloatLayout()

        # 🔹 Intro animasyonu
        self.intro = Image(
    source="assets/intro.gif",
    allow_stretch=True,     # tam ekran yayılmasına izin ver
    keep_ratio=True,        # oranı koru (şekil bozulmaz)
    size_hint=(1, 1),       # tüm ekranı kapla
    pos_hint={"center_x": 0.5, "center_y": 0.5}
)
        self.root.add_widget(self.intro)

        # 🔹 5 saniye sonra fade ile ana ekrana geç
        Clock.schedule_once(self.fade_out_intro, 5)
        return self.root

    def fade_out_intro(self, *args):
        anim = Animation(opacity=0, duration=1.2)
        anim.bind(on_complete=lambda *x: self.load_main_screen())
        anim.start(self.intro)

    def load_main_screen(self):
        self.root.clear_widgets()
        # 🔹 Burada senin ana ekran sınıfın (örneğin "Main") çağrılır 
        self.root.add_widget(Main())

if __name__ == "__main__":
    EnigmaxApp().run()