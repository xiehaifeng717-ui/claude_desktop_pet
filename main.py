import sys
import os
import math
import random
import subprocess
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QSystemTrayIcon, QAction
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QPainterPath, QFont,
    QIcon, QPixmap, QRadialGradient, QCursor, QFontMetrics,
    QPolygonF
)
from PyQt5.QtCore import QSharedMemory, QByteArray
from PyQt5.QtSvg import QSvgRenderer


# ─── Claude icon SVG ──────────────────────────────────────────────────
_CLAUDE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
<defs>
<radialGradient id="g" cx="35%" cy="35%" r="65%">
<stop offset="0%" stop-color="#FF9E4A"/>
<stop offset="55%" stop-color="#E8611A"/>
<stop offset="100%" stop-color="#CC4400"/>
</radialGradient>
</defs>
<path fill="url(#g)" fill-rule="evenodd" d="M4.709 15.955l4.72-2.647.08-.23-.08-.128H9.2l-.79-.048-2.698-.073-2.339-.097-2.266-.122-.571-.121L0 11.784l.055-.352.48-.321.686.06 1.52.103 2.278.158 1.652.097 2.449.255h.389l.055-.157-.134-.098-.103-.097-2.358-1.596-2.552-1.688-1.336-.972-.724-.491-.364-.462-.158-1.008.656-.722.881.06.225.061.893.686 1.908 1.476 2.491 1.833.365.304.145-.103.019-.073-.164-.274-1.355-2.446-1.446-2.49-.644-1.032-.17-.619a2.97 2.97 0 01-.104-.729L6.283.134 6.696 0l.996.134.42.364.62 1.414 1.002 2.229 1.555 3.03.456.898.243.832.091.255h.158V9.01l.128-1.706.237-2.095.23-2.695.08-.76.376-.91.747-.492.584.28.48.685-.067.444-.286 1.851-.559 2.903-.364 1.942h.212l.243-.242.985-1.306 1.652-2.064.73-.82.85-.904.547-.431h1.033l.76 1.129-.34 1.166-1.064 1.347-.881 1.142-1.264 1.7-.79 1.36.073.11.188-.02 2.856-.606 1.543-.28 1.841-.315.833.388.091.395-.328.807-1.969.486-2.309.462-3.439.813-.042.03.049.061 1.549.146.662.036h1.622l3.02.225.79.522.474.638-.079.485-1.215.62-1.64-.389-3.829-.91-1.312-.329h-.182v.11l1.093 1.068 2.006 1.81 2.509 2.33.127.578-.322.455-.34-.049-2.205-1.657-.851-.747-1.926-1.62h-.128v.17l.444.649 2.345 3.521.122 1.08-.17.353-.608.213-.668-.122-1.374-1.925-1.415-2.167-1.143-1.943-.14.08-.674 7.254-.316.37-.729.28-.607-.461-.322-.747.322-1.476.389-1.924.315-1.53.286-1.9.17-.632-.012-.042-.14.018-1.434 1.967-2.18 2.945-1.726 1.845-.414.164-.717-.37.067-.662.401-.589 2.388-3.036 1.44-1.882.93-1.086-.006-.158h-.055L4.132 18.56l-1.13.146-.487-.456.061-.746.231-.243 1.908-1.312-.006.006z"/>
</svg>'''

_CLAUDE_CODE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
<defs>
<linearGradient id="cg" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#FF9E4A"/>
<stop offset="50%" stop-color="#E8611A"/>
<stop offset="100%" stop-color="#CC4400"/>
</linearGradient>
</defs>
<path fill="url(#cg)" fill-rule="evenodd" clip-rule="evenodd" d="M20.998 10.949H24v3.102h-3v3.028h-1.487V20H18v-2.921h-1.487V20H15v-2.921H9V20H7.488v-2.921H6V20H4.487v-2.921H3V14.05H0V10.95h3V5h17.998v5.949zM6 10.949h1.488V8.102H6v2.847zm10.51 0H18V8.102h-1.49v2.847z"/>
</svg>'''

_CLAUDE_CODE_BODY = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
<defs>
<linearGradient id="cg" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#FF9E4A"/>
<stop offset="50%" stop-color="#E8611A"/>
<stop offset="100%" stop-color="#CC4400"/>
</linearGradient>
</defs>
<path fill="url(#cg)" fill-rule="evenodd" d="M20.998 10.949H24v3.102h-3v3.028h-1.487V20H18v-2.921h-1.487V20H15v-2.921H9V20H7.488v-2.921H6V20H4.487v-2.921H3V14.05H0V10.95h3V5h17.998v5.949z"/>
</svg>'''

# viewBox coords of the two eye holes in the original Claude Code icon
_CODE_EYE_L = (6, 8.102, 1.488, 2.847)     # x, y, w, h
_CODE_EYE_R = (16.512, 8.102, 1.488, 2.847)  # mirrored symmetric to left


# ─── Behavior states ───────────────────────────────────────────────────
class State:
    IDLE    = 'idle'
    WALK    = 'walk'
    SLEEP   = 'sleep'
    HAPPY   = 'happy'
    EAT     = 'eat'


# ─── Pet window ────────────────────────────────────────────────────────
class RoundedMenu(QMenu):
    """QMenu with DWM rounded corners (Win11)."""
    def showEvent(self, event):
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi
            val = wintypes.DWORD(2)
            dwm.DwmSetWindowAttribute(
                wintypes.HWND(hwnd), 33, ctypes.byref(val), ctypes.sizeof(val)
            )
        except Exception:
            pass


class PetWindow(QWidget):
    SIZE = 140          # window size (square)

    def __init__(self):
        super().__init__()
        # ── window flags ────────────────────────────────────────────
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.SIZE, self.SIZE + 20)  # extra space for feet
        self.setMouseTracking(True)
        self._apply_round_mask()

        # ── SVG renderers ─────────────────────────────────────────
        self._svg_renderers = [
            QSvgRenderer(QByteArray(_CLAUDE_SVG.encode('utf-8'))),
            QSvgRenderer(QByteArray(_CLAUDE_CODE_SVG.encode('utf-8'))),
        ]
        self._code_body_renderer = QSvgRenderer(QByteArray(_CLAUDE_CODE_BODY.encode('utf-8')))
        self._icon_id = 1   # 0=Claude, 1=Claude Code (default)

        # ── pet state ───────────────────────────────────────────────
        self.state          = State.IDLE
        self.hunger         = 100.0        # 0-100
        self.happiness      = 80.0         # 0-100
        self.energy         = 100.0         # 0-100
        self.blink          = 0
        self.eye_openness   = 1.0
        self.eye_target_dir = 0.0, 0.0
        self.walk_progress  = 0.0
        self.walk_dir       = 1.0, 0.0
        self.frame          = 0
        self.sleep_z_count  = 0
        self._forced_sleep  = False     # manual sleep lock
        self._feed_particles = []        # (x, y, life, max_life) for heart particles
        self._bubble = None              # (text, age, duration) for idle bubble

        # ── interaction ─────────────────────────────────────────────
        self.dragging   = False
        self.drag_offset = QPoint()
        self.mouse_in   = False

        # ── timers ──────────────────────────────────────────────────
        self.tick = QTimer(self)
        self.tick.timeout.connect(self._tick)
        self.tick.start(33)                 # ~30 fps

        self.behave = QTimer(self)
        self.behave.timeout.connect(self._behave)
        self.behave.start(1500)             # behaviour evaluation

        # ── screen & init pos ───────────────────────────────────────
        self.screen_geom = QApplication.primaryScreen().geometry()
        self._w = self.width()
        self._h = self.height()

        start_x = random.randint(0, self.screen_geom.width() - self._w)
        start_y = random.randint(0, self.screen_geom.height() - self._h)
        self.move(start_x, start_y)
        self._pick_walk_target()

        # ── build tray ──────────────────────────────────────────────
        self._build_tray()

    # ──────────────────────── bounds clamp ─────────────────────────────
    def move(self, x, y):
        """Clamp position so the pet never goes off-screen."""
        sg = self.screen_geom
        x = max(sg.x(), min(x, sg.x() + sg.width() - self._w))
        y = max(sg.y(), min(y, sg.y() + sg.height() - self._h))
        super().move(x, y)

    def _apply_round_mask(self):
        """Use Windows DWM to set rounded corners (Win11)."""
        try:
            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33
            # DWMWA_ROUND_PREFERENCE: 0=default, 1=don't round, 2=round, 3=round small
            val = wintypes.DWORD(2)
            dwm.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                33,
                ctypes.byref(val),
                ctypes.sizeof(val)
            )
        except Exception:
            pass  # dwmapi not available (Win10 or older)

    # ───────────────────────────── paint ──────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cw, ch = self.width(), self.height()
        cx, cy = cw // 2, ch // 2 - 10      # body center

        # shadow
        self._draw_shadow(p, cx, cy)

        # body (Claude C)
        self._draw_body(p, cx, cy)

        # eyes
        self._draw_eyes(p, cx, cy)

        # feet
        self._draw_feet(p, cx, cy)

        # antenna
        self._draw_antenna(p, cx, cy)

        # state overlays
        if self.state == State.SLEEP:
            self._draw_zs(p, cx, cy)
        elif self.state == State.HAPPY:
            self._draw_hearts(p, cx, cy)

        # feed particles (always on top)
        self._draw_feed_particles(p)

        # idle bubble
        self._draw_bubble(p, cx, cy)

        # hunger bar (always subtle)
        self._draw_hunger_bar(p, cx, cy)

    # ── body: Claude (C) or Claude Code (terminal) ─────────────────────
    def _draw_body(self, p, cx, cy):
        if self._icon_id == 0:
            size = 88
            rect = QRectF(cx - size / 2, cy - size / 2, size, size)
            self._svg_renderers[0].render(p, rect)
            return rect
        else:
            return self._draw_body_code(p, cx, cy)

    def _draw_body_code(self, p, cx, cy):
        size = 80
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)
        self._code_body_renderer.render(p, rect)
        # punch eye holes
        s = size / 24.0
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        open_factor = 0.22 if self.state == State.SLEEP else self.eye_openness
        for ex, ey, ew, eh in [_CODE_EYE_L, _CODE_EYE_R]:
            h = eh * s * max(open_factor, 0.04)
            h = min(h, eh * s)  # cap at full eye height
            p.drawRect(QRectF(
                cx - size/2 + ex * s,
                cy - size/2 + ey * s + (eh * s - h) / 2,
                ew * s,
                h
            ))
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        return rect

    # ── eyes ───────────────────────────────────────────────────────────
    def _draw_eyes(self, p, cx, cy):
        if self._icon_id == 0:
            self._draw_eyes_claude(p, cx, cy)
        else:
            self._draw_eyes_code(p, cx, cy)

    def _draw_eyes_claude(self, p, cx, cy):
        if self.state == State.SLEEP:
            p.setPen(QPen(QColor('#2D1B00'), 2.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx-12, cy-6), QPointF(cx-6, cy-4))
            p.drawLine(QPointF(cx+6, cy-4), QPointF(cx+12, cy-6))
            return

        openness = self.eye_openness
        dx, dy = self.eye_target_dir
        eye_l = QPointF(cx - 11 + dx*3, cy - 2 + dy*3)
        eye_r = QPointF(cx + 11 + dx*3, cy - 2 + dy*3)
        eye_r_ad = 5.5

        if openness < 0.1:
            return

        for ex, ey in [(eye_l.x(), eye_l.y()), (eye_r.x(), eye_r.y())]:
            p.setBrush(QColor('#FFFFFF'))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(ex, ey), eye_r_ad, eye_r_ad * openness)
            pr = 2.8
            p.setBrush(QColor('#2D1B00'))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(ex + dx*1.5, ey + dy*1.5), pr, pr * openness)
            p.setBrush(QColor('#FFFFFF'))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(ex + dx*1.5 - 1.5, ey + dy*1.5 - 1.5 * openness), 1.2, 1.2 * openness)

        p.setBrush(QColor(255, 120, 80, 50))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx - 17, cy + 5), 5, 3)
        p.drawEllipse(QPointF(cx + 17, cy + 5), 5, 3)

    def _draw_eyes_code(self, p, cx, cy):
        """No drawn eyes — the SVG cutout holes are the eyes.
        Blink is handled by _draw_body_code punching/not punching holes."""
        # blush only
        if self.state != State.SLEEP:
            p.setBrush(QColor(255, 120, 80, 50))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx - 16, cy + 5), 4, 3)
            p.drawEllipse(QPointF(cx + 16, cy + 5), 4, 3)

    # ── feet ───────────────────────────────────────────────────────────
    def _draw_feet(self, p, cx, cy):
        if self._icon_id == 0:
            self._draw_feet_claude(p, cx, cy)
        # Claude Code icon has no feet

    def _draw_feet_claude(self, p, cx, cy):
        bounce = 0
        if self.state == State.WALK:
            bounce = abs(math.sin(self.walk_progress * math.pi * 2)) * 4

        body_bottom = cy + 42
        for side in [-1, 1]:
            fx = cx + side * 12
            fy = body_bottom + 6 + bounce * (1 if side == -1 else 0.5)

            p.setBrush(QColor('#E8611A'))
            p.setPen(QPen(QColor('#B33A00'), 1.5))
            p.drawRoundedRect(int(fx-6), int(fy), 12, 8, 3, 3)

    # ── antenna ────────────────────────────────────────────────────────
    def _draw_antenna(self, p, cx, cy):
        if self._icon_id == 0:
            self._draw_antenna_claude(p, cx, cy)
        # Claude Code icon has no antenna

    def _draw_antenna_claude(self, p, cx, cy):
        top_x = cx
        top_y = cy - 48 + math.sin(self.frame * 0.05) * 2
        p.setPen(QPen(QColor('#E8611A'), 2.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy - 36), QPointF(top_x, top_y))
        p.setBrush(QColor('#FF9E4A'))
        p.setPen(QPen(QColor('#CC4400'), 1.5))
        p.drawEllipse(QPointF(top_x, top_y), 4, 4)

    # ── shadow ─────────────────────────────────────────────────────────
    def _draw_shadow(self, p, cx, cy):
        ground_y = cy + 55
        shade = QRadialGradient(cx, ground_y, 35)
        shade.setColorAt(0.0, QColor(0, 0, 0, 50))
        shade.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(shade))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, ground_y), 35, 8)

    # ── Z's (sleep) ───────────────────────────────────────────────────
    def _draw_zs(self, p, cx, cy):
        if self._icon_id == 0:
            self._draw_zs_claude(p, cx, cy)
        else:
            self._draw_zs_code(p, cx, cy)

    def _draw_zs_claude(self, p, cx, cy):
        p.setFont(QFont('Segoe UI', 9, QFont.Bold))
        p.setPen(QColor('#B8D4FF'))
        zs = ['z', 'Z', 'z']
        for i, z in enumerate(zs):
            offset = (self.frame * 0.02 + i * 0.3) % 1
            px = cx + 30 + i * 8
            py = cy - 30 - i * 12 - offset * 10
            p.setOpacity(1.0 - offset * 0.5)
            p.drawText(int(px), int(py), z)
        p.setOpacity(1.0)

    def _draw_zs_code(self, p, cx, cy):
        p.setFont(QFont('Consolas', 8, QFont.Bold))
        p.setPen(QColor('#B8D4FF'))
        zs = ['Z', 'z', 'z']
        for i, z in enumerate(zs):
            offset = (self.frame * 0.02 + i * 0.35) % 1
            px = cx + 15 + i * 10
            py = cy - 10 - i * 10 - offset * 8
            p.setOpacity(1.0 - offset * 0.5)
            p.drawText(int(px), int(py), z)
        p.setOpacity(1.0)

    # ── hearts (happy) ──────────────────────────────────────────────────
    def _draw_hearts(self, p, cx, cy):
        p.setPen(Qt.NoPen)
        ox = 35 if self._icon_id == 0 else 20
        oy = 25 if self._icon_id == 0 else 15
        for i in range(3):
            t = (self.frame * 0.03 + i * 0.4) % 1
            px = cx + ox + i * 12 - 10
            py = cy - oy - i * 15 - t * 20
            sz = 4 + t * 2
            alpha = int(200 * (1 - t))
            p.setBrush(QColor(255, 100, 100, alpha))
            p.drawEllipse(QPointF(px, py), sz, sz)

    # ── hunger bar ─────────────────────────────────────────────────────
    def _draw_hunger_bar(self, p, cx, cy):
        bar_w, bar_h = 50, 4
        bx, by = cx - bar_w//2, cy + 52
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawRoundedRect(bx, by, bar_w, bar_h, 2, 2)
        ratio = max(0, self.hunger / 100)
        color = QColor(
            int(255 * (1 - ratio)),
            int(200 * ratio),
            60
        )
        p.setBrush(color)
        p.drawRoundedRect(bx, by, int(bar_w * ratio), bar_h, 2, 2)

    # ── idle bubble ──────────────────────────────────────────────────
    _BUBBLE_TEXTS = ['💭', '🎵', '❓', '✨', '😊', '💤', '👀', '✌️']

    def _draw_bubble(self, p, cx, cy):
        if self._bubble is None:
            return
        text, age, duration = self._bubble
        t = age / duration
        alpha = int(230 * (1 - t)) if t > 0.7 else 230
        if alpha < 20:
            return
        p.setFont(QFont('Segoe UI Emoji', 11, QFont.Bold))
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        pad_x, pad_y = 8, 5
        bw = max(tw + pad_x * 2, 28)
        bh = th + pad_y * 2
        bx = cx - bw // 2
        by = max(3, cy - 42 - bh)  # pinned below window top

        p.setPen(QPen(QColor(200, 200, 200, alpha), 1))
        p.setBrush(QColor(255, 255, 255, alpha))
        p.drawRoundedRect(bx, by, bw, bh, 6, 6)

        # tail
        tail = QPolygonF([
            QPointF(cx - 4, by + bh),
            QPointF(cx, by + bh + 6),
            QPointF(cx + 4, by + bh),
        ])
        p.setBrush(QColor(255, 255, 255, alpha))
        p.setPen(Qt.NoPen)
        p.drawPolygon(tail)

        p.setPen(QColor('#2D1B00'))
        p.setBrush(Qt.NoBrush)
        text_y = by + (bh - th) // 2 + fm.ascent()
        p.drawText(int(bx + pad_x), int(text_y), text)

    # ── feed particles (hearts only) ───────────────────────────────
    def _draw_feed_particles(self, p):
        if not self._feed_particles:
            return
        p.setPen(Qt.NoPen)
        for px, py, age, max_life in self._feed_particles:
            t = age / max_life
            if t > 0.9:
                continue
            sz = 12
            p.setBrush(QColor(255, 40, 60, 230))
            hp = QPainterPath()
            hp.moveTo(px, py + sz * 0.55)
            hp.cubicTo(px - sz * 0.4, py + sz * 0.25,
                       px - sz * 0.75, py + sz * 0.05,
                       px - sz * 0.55, py - sz * 0.3)
            hp.cubicTo(px - sz * 0.4, py - sz * 0.55,
                       px - sz * 0.1, py - sz * 0.55,
                       px, py - sz * 0.12)
            hp.cubicTo(px + sz * 0.1, py - sz * 0.55,
                       px + sz * 0.4, py - sz * 0.55,
                       px + sz * 0.55, py - sz * 0.3)
            hp.cubicTo(px + sz * 0.75, py + sz * 0.05,
                       px + sz * 0.4, py + sz * 0.25,
                       px, py + sz * 0.55)
            hp.closeSubpath()
            p.drawPath(hp)

    # ──────────────────────────── tick ─────────────────────────────────
    def _tick(self):
        self.frame += 1

        # ── blink ───────────────────────────────────────────────────
        if self.state != State.SLEEP:
            self.blink += 1
            if self.blink > 120 + random.randint(0, 80):
                self.blink = 0
                # close → open animation via eye_openness
                self.eye_openness = 0.0
            else:
                # gradually re-open if closed
                self.eye_openness = min(1.0, self.eye_openness + 0.08)
        else:
            self.eye_openness = 0.0

        # ── idle bubble ───────────────────────────────────────────
        if self.state == State.IDLE and self._bubble is None and random.random() < 0.008:
            self._bubble = (random.choice(self._BUBBLE_TEXTS), 0, 120 + random.randint(0, 60))
        if self._bubble:
            t, a, d = self._bubble
            a += 1
            if a >= d:
                self._bubble = None
            else:
                self._bubble = (t, a, d)

        # ── idle eye movement ──────────────────────────────────────
        if random.random() < 0.02:
            self.eye_target_dir = (
                (random.random() - 0.5) * 0.6,
                (random.random() - 0.5) * 0.6,
            )

        # ── stats decay ────────────────────────────────────────────
        self.hunger    = max(0, self.hunger - 0.008)
        self.happiness = max(0, self.happiness - 0.003)
        if self.state != State.SLEEP:
            self.energy = min(100, self.energy + 0.002)
        else:
            self.energy = min(100, self.energy + 0.03)

        # ── walk movement ──────────────────────────────────────────
        if self.state == State.WALK:
            self.walk_progress += 0.015
            sx, sy = self.walk_dir
            spd = 2.2
            dx = sx * math.cos(self.walk_progress * 0.5) * spd
            dy = sy * spd * 0.5

            new_x = self.x() + round(dx)
            new_y = self.y() + round(dy)

            # bounce off screen edges
            sg = self.screen_geom
            clamped_x = max(sg.x(), min(new_x, sg.x() + sg.width() - self._w))
            clamped_y = max(sg.y(), min(new_y, sg.y() + sg.height() - self._h))
            if new_x != clamped_x:
                sx = -sx
            if new_y != clamped_y:
                sy = -sy
            self.walk_dir = (sx, sy)

            self.move(new_x, new_y)

        # ── feed particles ────────────────────────────────────────
        for p in self._feed_particles[:]:
            p[0] += random.uniform(-1.0, 0.2)   # spread left
            p[1] -= 0.9 + random.uniform(0, 0.5)  # float up at varied speed
            p[2] += 1
            if p[2] >= p[3]:
                self._feed_particles.remove(p)

        self.update()

    # ─────────────────────────── behaviour ─────────────────────────────
    def _behave(self):
        if self.dragging:
            return

        # low hunger → feed self
        if self.hunger < 20 and self.energy > 20:
            self._enter_state(State.EAT)
            self.hunger = min(100, self.hunger + 30)
            self.energy = max(0, self.energy - 5)
            return

        # low energy → sleep (only if not forced awake)
        if self.energy < 15 and not self._forced_sleep:
            self._enter_state(State.SLEEP)
            return

        # random state transitions
        r = random.random()
        if self.state == State.IDLE:
            if r < 0.35:
                self._enter_state(State.WALK)
            elif r < 0.4:
                self._enter_state(State.HAPPY)
            elif r < 0.45 and self.energy < 30 and not self._forced_sleep:
                self._enter_state(State.SLEEP)
        elif self.state == State.WALK:
            if r < 0.15:
                self._enter_state(State.IDLE)
            elif r < 0.2:
                self._enter_state(State.HAPPY)
        elif self.state == State.HAPPY:
            if r < 0.3:
                self._enter_state(State.IDLE)
        elif self.state == State.SLEEP:
            # only auto-wake if not in forced sleep
            if not self._forced_sleep and (self.energy > 85 or r < 0.05):
                self._enter_state(State.IDLE)
        elif self.state == State.EAT:
            self._enter_state(State.HAPPY)

    def _enter_state(self, new_state):
        if self.state == new_state:
            return
        self.state = new_state

        if new_state == State.WALK:
            self._pick_walk_target()
        elif new_state == State.SLEEP:
            self.sleep_z_count = 0
        elif new_state == State.HAPPY:
            self.happiness = min(100, self.happiness + 5)

    def _pick_walk_target(self):
        angle = random.random() * math.pi * 2
        self.walk_dir = (math.cos(angle), math.sin(angle))
        self.walk_progress = 0

    # ───────────────────────── mouse events ────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_offset = event.pos()
            self.mouse_in = True

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(
                event.globalX() - self.drag_offset.x(),
                event.globalY() - self.drag_offset.y()
            )
        self.mouse_in = True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            # small happy reaction
            if self.state != State.SLEEP:
                self._enter_state(State.HAPPY)
        self.mouse_in = False

    def enterEvent(self, event):
        self.mouse_in = True

    def leaveEvent(self, event):
        self.mouse_in = False

    # ──────────────────────── context menu ─────────────────────────────
    def contextMenuEvent(self, event):
        menu = RoundedMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF; color: #333; border: 1px solid #D0D0D0;
                border-radius: 8px; padding: 4px; font-size: 12px;
            }
            QMenu::item { padding: 5px 22px; border-radius: 4px; }
            QMenu::item:selected { background: #E8611A; color: #FFF; }
            QMenu::separator { height: 1px; background: #E8E8E8; margin: 3px 8px; }
        """)

        menu.addAction('🍖  投喂').triggered.connect(lambda: self._feed())
        menu.addSeparator()
        if self._forced_sleep or self.state == State.SLEEP:
            menu.addAction('☀️  唤醒').triggered.connect(lambda: self._wake())
        else:
            menu.addAction('💤  睡觉').triggered.connect(lambda: self._sleep_forced())
        menu.addSeparator()
        menu.addAction('🔄  切换图标').triggered.connect(lambda: self._toggle_icon())
        menu.addAction('>_  Claude Code').triggered.connect(self._launch_claude_code)
        menu.addSeparator()
        menu.addAction('🔄  重启').triggered.connect(self._restart)
        menu.addAction('❌  退出').triggered.connect(QApplication.quit)

        menu.exec(event.globalPos())

    def _feed(self):
        self.hunger = min(100, self.hunger + 25)
        self._enter_state(State.EAT)
        # spawn hearts from top-right of icon
        cw, ch = self.width(), self.height()
        cx, cy = cw // 2, ch // 2 - 10
        for _ in range(6):
            self._feed_particles.append([
                cx + random.randint(10, 50),
                cy + random.randint(-42, -12),
                0,
                55 + random.randint(0, 25),
            ])

    def _toggle_icon(self):
        self._icon_id = 1 - self._icon_id
        self.update()

    def _restart(self):
        """Restart the pet process."""
        QTimer.singleShot(0, self._do_restart)

    def _do_restart(self):
        _shared_mem.detach()
        bat = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_pet.bat')
        subprocess.Popen([bat], creationflags=subprocess.CREATE_NO_WINDOW)
        os._exit(0)

    def _launch_claude_code(self):
        """Launch Claude Code CLI (working dir: D:/)."""
        try:
            exe = (
                r'C:\Users\29283\AppData\Roaming\npm\node_modules'
                r'\@anthropic-ai\claude-code\bin\claude.exe'
            )
            subprocess.Popen(
                [exe],
                cwd='D:\\',
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            print(f'[pet] launch error: {e}')

    def _sleep_forced(self):
        """Put the pet to sleep permanently (until explicitly woken)."""
        self._forced_sleep = True
        self._enter_state(State.SLEEP)

    def _wake(self):
        """Wake the pet from forced sleep."""
        self._forced_sleep = False
        self._enter_state(State.IDLE)
        self.happiness = min(100, self.happiness + 3)

    # ──────────────────────── system tray ──────────────────────────────
    def _build_tray(self):
        # create a minimal tray icon
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        g = QRadialGradient(16, 16, 14, 12, 10)
        g.setColorAt(0, QColor('#FF9E4A'))
        g.setColorAt(1, QColor('#CC4400'))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 2, 28, 28, 6, 6)
        p.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pix), self)
        tray_menu = RoundedMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF; color: #333; border: 1px solid #D0D0D0;
                border-radius: 8px; padding: 4px; font-size: 12px;
            }
            QMenu::item { padding: 5px 22px; border-radius: 4px; }
            QMenu::item:selected { background: #E8611A; color: #FFF; }
            QMenu::separator { height: 1px; background: #E8E8E8; margin: 3px 8px; }
        """)
        tray_menu.addAction('🐾  显示').triggered.connect(self.show)
        tray_menu.addAction('🔄  重置位置').triggered.connect(
            lambda: self.move(
                random.randint(100, self.screen_geom.width() - 200),
                random.randint(100, self.screen_geom.height() - 200)
            )
        )
        tray_menu.addSeparator()
        tray_menu.addAction('❌  退出').triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(
            lambda reason: self.show() if reason == QSystemTrayIcon.DoubleClick else None
        )
        self.tray_icon.show()


# ─── Single instance guard ──────────────────────────────────────────────
_shared_mem = None


def _is_already_running():
    """Return True if another instance is already running."""
    global _shared_mem
    _shared_mem = QSharedMemory('ClaudeDesktopPet_InstanceLock')
    if _shared_mem.attach():
        return True
    _shared_mem.create(1)
    return False


# ─── Entry point ───────────────────────────────────────────────────────
def main():
    if _is_already_running():
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setQuitOnLastWindowClosed(False)

    w = PetWindow()
    w.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
