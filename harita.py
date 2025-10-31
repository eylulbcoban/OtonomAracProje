import pygame, math


class Harita:
    def __init__(self, genislik=1500, yukseklik=700):
        pygame.init()
        self.GENISLIK, self.YUKSEKLIK = genislik, yukseklik
        self.ekran = pygame.display.set_mode((self.GENISLIK, self.YUKSEKLIK))
        pygame.display.set_caption("Izgara Yolları — Hareketli Araç & Panel")
        self.saat = pygame.time.Clock()

        # Renkler ve stiller
        self.CIMEN = (188, 224, 186)
        self.ASFALT = (90, 90, 90)
        self.SERIT = (255, 255, 255)
        self.YOL_KALINLIK = int(min(self.GENISLIK, self.YUKSEKLIK) * 0.082)
        self.SERIT_KALINLIK = max(4, self.YOL_KALINLIK // 10)

        # Trafik ışığı renkleri
        self.STOP_LINE_RENK = (255, 0, 0)
        self.ISIK_KUTU = (30, 30, 30)
        self.KAPALI_KIRMIZI = (100, 0, 0)
        self.KAPALI_SARI = (100, 100, 0)
        self.KAPALI_YESIL = (0, 100, 0)
        self.ACIK_KIRMIZI = (255, 0, 0)
        self.ACIK_SARI = (255, 255, 0)
        self.ACIK_YESIL = (0, 255, 0)

        # Panel renkleri & font
        self.KUTU_BG = (240, 240, 240)
        self.KUTU_KENAR = (100, 100, 100)
        self.OK_RENK = (50, 50, 50)
        self.YAZI_RENK = (30, 30, 30)
        try:
            self.BASLIK_FONT = pygame.font.SysFont("Arial", 28, bold=True)
        except Exception:
            self.BASLIK_FONT = pygame.font.Font(None, 34)
        try:
            self.BUTON_FONT = pygame.font.SysFont("Arial", 18, bold=True)
        except Exception:
            self.BUTON_FONT = pygame.font.Font(None, 24)
        try:
            self.SENSOR_FONT = pygame.font.SysFont("Arial", 20, bold=True)
        except Exception:
            self.SENSOR_FONT = pygame.font.Font(None, 28)

        # Izgara
        self.SUTUN, self.SATIR = 20, 12
        self.KENAR_BOSLUK = int(min(self.GENISLIK / self.SUTUN, self.YUKSEKLIK / self.SATIR) * 0.3) if self.SUTUN > 0 and self.SATIR > 0 else 20
        self.HUCRE = min((self.GENISLIK - 2 * self.KENAR_BOSLUK) / self.SUTUN, (self.YUKSEKLIK - 2 * self.KENAR_BOSLUK) / self.SATIR) if self.SUTUN > 0 and self.SATIR > 0 else 50
        self.OFFSET_X = 80
        self.OFFSET_Y = 50

        # Panel ayarları
        self.KUTU_GENISLIK = 200
        self.KUTU_YUKSEKLIK = 450
        self.KUTU_Y = (self.YUKSEKLIK - self.KUTU_YUKSEKLIK) / 2
        self.KUTU_X_ACIK = self.GENISLIK - self.KUTU_GENISLIK
        self.KUTU_X_KAPALI = self.GENISLIK
        self.OK_SEKME_GENISLIK = 20
        self.OK_SEKME_YUKSEKLIK = 80
        self.OK_SEKME_Y = (self.YUKSEKLIK - self.OK_SEKME_YUKSEKLIK) / 2
        self.kutu_acik = False
        self.ok_rect = pygame.Rect(0, 0, 0, 0)

        # Yollar
        self.yollar = self._olustur_yollar()
        self.KAVSAK_MERKEZ_1 = self.kose(7, 6)
        self.KAVSAK_MERKEZ_2 = self.kose(13, 6)
        self.KAVSAK_YARICAP = int(self.HUCRE * 1.5)

        # Buton rect referansları
        self.BTN_ADD_YAYA = None
        self.BTN_ADD_CALISMA = None
        self.BTN_ADD_KASIS = None
        self.BTN_ADD_ISIK = None
        self.BTN_DELETE = None
        self.BTN_ROTATE = None
        self.BTN_LONGER = None
        self.BTN_SHORTER = None
        self.panel_sayfa = 0

    def kose(self, c, r):
        return (
            self.KENAR_BOSLUK + self.OFFSET_X + c * self.HUCRE,
            self.KENAR_BOSLUK + self.OFFSET_Y + r * self.HUCRE,
        )

    def _olustur_yollar(self):
        k = self.kose
        return [
            [k(2, 2), k(18, 2)],
            [k(2, 6), k(18, 6)],
            [k(2, 10), k(18, 10)],
            [k(4, 2), k(4, 10)],
            [k(10, 2), k(10, 10)],
            [k(16, 2), k(16, 10)],
            [k(7, 2), k(7, 6)],
            [k(13, 2), k(13, 6)],
            [k(7, 6), k(7, 10)],
            [k(13, 6), k(13, 10)],
            [k(4, 4), k(16, 4)],
            [k(4, 8), k(16, 8)],
            [k(18, 5), k(18, 8)],
            [k(16, 8), k(18, 8)],
            [k(2, 2), k(4, 2)],
            [k(2, 10), k(4, 10)],
            [k(7, 2), k(7, 0)],
            [k(10, 2), k(10, 0)],
            [k(7, 0), k(10, 0)],
            [k(2, 2), k(2, 10)],
            [k(18, 2), k(18, 10)],
            [k(2, 10), k(0, 10)],
            [k(18, 2), k(20, 2)],
            [k(18, 6), k(20, 6), k(20, 8)],
            [k(2, 2), k(0, 2), k(0, 0)],
        ]

    # Çizim yardımcıları
    def yol_yuzeyi_ciz(self, noktalar, genislik, renk):
        pygame.draw.lines(self.ekran, renk, False, noktalar, genislik)
        yaricap = genislik // 2
        for x, y in noktalar:
            pygame.draw.circle(self.ekran, renk, (int(x), int(y)), yaricap)

    def kesikli_serit(self, noktalar, uzunluk=None, bosluk=None):
        if uzunluk is None:
            uzunluk = int(self.YOL_KALINLIK * 0.8)
        if bosluk is None:
            bosluk = int(self.YOL_KALINLIK * 0.6)
        aralik = uzunluk + bosluk
        for (x1, y1), (x2, y2) in zip(noktalar[:-1], noktalar[1:]):
            d = math.hypot(x2 - x1, y2 - y1)
            if d == 0:
                continue
            ux, uy = (x2 - x1) / d, (y2 - y1) / d
            t = 0
            while t < d:
                a = (x1 + ux * t, y1 + uy * t)
                b = (x1 + ux * min(t + uzunluk, d), y1 + uy * min(t + uzunluk, d))
                pygame.draw.line(self.ekran, self.SERIT, a, b, self.SERIT_KALINLIK)
                t += aralik

    def yol_ciz(self, noktalar):
        self.yol_yuzeyi_ciz(noktalar, self.YOL_KALINLIK, self.ASFALT)
        self.kesikli_serit(noktalar)

    def doner_kavsak_ciz(self, merkez, dis_yaricap):
        ic_yaricap = dis_yaricap - self.YOL_KALINLIK
        pygame.draw.circle(self.ekran, self.ASFALT, merkez, int(dis_yaricap))
        ada_yaricap = max(8, int(ic_yaricap * 0.99))
        pygame.draw.circle(self.ekran, self.CIMEN, merkez, ada_yaricap)
        orta = (dis_yaricap + ic_yaricap) / 2
        for a in range(0, 360, 34):
            a1 = math.radians(a)
            a2 = math.radians(a + 18)
            p1 = (merkez[0] + orta * math.cos(a1), merkez[1] + orta * math.sin(a1))
            p2 = (merkez[0] + orta * math.cos(a2), merkez[1] + orta * math.sin(a2))
            pygame.draw.line(self.ekran, self.SERIT, p1, p2, self.SERIT_KALINLIK)

    def sensor_paneli_ciz(self, sensor_degerleri):
        panel_rect = pygame.Rect(20, 20, 200, 90)
        pygame.draw.rect(self.ekran, (245, 245, 245), panel_rect, border_radius=10)
        pygame.draw.rect(self.ekran, (80, 80, 80), panel_rect, 2, border_radius=10)
        etiketler = ["Sol", "Orta", "Sağ"]
        for i, deger in enumerate(sensor_degerleri):
            text = f"{etiketler[i]}: {deger:>3} px"
            yaziyuzeyi = self.SENSOR_FONT.render(text, True, (0, 0, 0))
            self.ekran.blit(yaziyuzeyi, (35, 30 + i * 25))

    def panel_ciz(self):
        # Panel dış sekmesi
        ok_sekme_x_pos = self.KUTU_X_KAPALI - self.OK_SEKME_GENISLIK

        if self.kutu_acik:
            kutu_x = self.KUTU_X_ACIK
            ok_sekme_x_pos = kutu_x - self.OK_SEKME_GENISLIK
            kutu_rect = pygame.Rect(kutu_x, self.KUTU_Y, self.KUTU_GENISLIK, self.KUTU_YUKSEKLIK)
            pygame.draw.rect(self.ekran, self.KUTU_BG, kutu_rect)
            pygame.draw.rect(self.ekran, self.KUTU_KENAR, kutu_rect, 3)

            baslik = self.BASLIK_FONT.render("Engeller", True, self.YAZI_RENK)
            self.ekran.blit(baslik, baslik.get_rect(center=(kutu_x + self.KUTU_GENISLIK / 2, self.KUTU_Y + 35)))
            pygame.draw.line(self.ekran, self.KUTU_KENAR, (kutu_x + 20, self.KUTU_Y + 60), (kutu_x + self.KUTU_GENISLIK - 20, self.KUTU_Y + 60), 2)

            butonlar = [
                ("+ Yaya Geçidi Ekle", "BTN_ADD_YAYA"),
                ("+ Yol Çalışması Ekle", "BTN_ADD_CALISMA"),
                ("+ Kasis Ekle", "BTN_ADD_KASIS"),
                ("+ Trafik Işığı Ekle", "BTN_ADD_ISIK"),
                ("Seçileni Sil", "BTN_DELETE"),
                ("Seçileni Döndür (90°)", "BTN_ROTATE"),
                ("Seçileni Uzat (+)", "BTN_LONGER"),
                ("Seçileni Kısalt (-)", "BTN_SHORTER"),
            ]
            SAYFA_BASINA = 4
            toplam_sayfa = max(1, math.ceil(len(butonlar) / SAYFA_BASINA))
            aktif_sayfa = max(0, min(self.panel_sayfa, toplam_sayfa - 1))

            start_i = aktif_sayfa * SAYFA_BASINA
            gorunen = butonlar[start_i:start_i + SAYFA_BASINA]
            bx, by = kutu_x + 20, self.KUTU_Y + 80
            bw, bh, gap = self.KUTU_GENISLIK - 40, 40, 10

            def buton_ciz(rect, etiket):
                pygame.draw.rect(self.ekran, (255, 255, 255), rect, border_radius=6)
                pygame.draw.rect(self.ekran, (120, 120, 120), rect, 2, border_radius=6)
                yazi = self.BUTON_FONT.render(etiket, True, (20, 20, 20))
                self.ekran.blit(yazi, yazi.get_rect(center=rect.center))

            rectler = {}
            for i, (etiket, ad) in enumerate(gorunen):
                rect = pygame.Rect(bx, by + i * (bh + gap), bw, bh)
                buton_ciz(rect, etiket)
                rectler[ad] = rect

            self.BTN_ADD_YAYA = rectler.get("BTN_ADD_YAYA")
            self.BTN_ADD_CALISMA = rectler.get("BTN_ADD_CALISMA")
            self.BTN_ADD_KASIS = rectler.get("BTN_ADD_KASIS")
            self.BTN_ADD_ISIK = rectler.get("BTN_ADD_ISIK")
            self.BTN_DELETE = rectler.get("BTN_DELETE")
            self.BTN_ROTATE = rectler.get("BTN_ROTATE")
            self.BTN_LONGER = rectler.get("BTN_LONGER")
            self.BTN_SHORTER = rectler.get("BTN_SHORTER")

            # Sayfa okları
            sol_ok = pygame.Rect(kutu_x + 25, self.KUTU_Y + self.KUTU_YUKSEKLIK - 45, 35, 25)
            sag_ok = pygame.Rect(kutu_x + self.KUTU_GENISLIK - 60, self.KUTU_Y + self.KUTU_YUKSEKLIK - 45, 35, 25)
            pygame.draw.rect(self.ekran, (230, 230, 230), sol_ok, border_radius=6)
            pygame.draw.rect(self.ekran, (230, 230, 230), sag_ok, border_radius=6)
            pygame.draw.polygon(self.ekran, (40, 40, 40), [(sol_ok.centerx + 5, sol_ok.centery - 7), (sol_ok.centerx - 5, sol_ok.centery), (sol_ok.centerx + 5, sol_ok.centery + 7)])
            pygame.draw.polygon(self.ekran, (40, 40, 40), [(sag_ok.centerx - 5, sag_ok.centery - 7), (sag_ok.centerx + 5, sag_ok.centery), (sag_ok.centerx - 5, sag_ok.centery + 7)])
            sayfa_text = self.BUTON_FONT.render(f"Sayfa {aktif_sayfa + 1}/{toplam_sayfa}", True, (50, 50, 50))
            self.ekran.blit(sayfa_text, (kutu_x + self.KUTU_GENISLIK / 2 - 45, self.KUTU_Y + self.KUTU_YUKSEKLIK - 40))

            if pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                if sol_ok.collidepoint((mx, my)) and aktif_sayfa > 0:
                    self.panel_sayfa = aktif_sayfa - 1
                elif sag_ok.collidepoint((mx, my)) and aktif_sayfa < toplam_sayfa - 1:
                    self.panel_sayfa = aktif_sayfa + 1
        else:
            self.BTN_ADD_YAYA = None
            self.BTN_ADD_CALISMA = None
            self.BTN_ADD_KASIS = None
            self.BTN_ADD_ISIK = None
            self.BTN_DELETE = None
            self.BTN_ROTATE = None
            self.BTN_LONGER = None
            self.BTN_SHORTER = None

        # Ok sekmesi
        self.ok_rect = pygame.Rect(ok_sekme_x_pos, self.OK_SEKME_Y, self.OK_SEKME_GENISLIK, self.OK_SEKME_YUKSEKLIK)
        pygame.draw.rect(self.ekran, self.KUTU_BG, self.ok_rect, border_top_left_radius=8, border_bottom_left_radius=8)
        pygame.draw.rect(self.ekran, self.KUTU_KENAR, self.ok_rect, 2, border_top_left_radius=8, border_bottom_left_radius=8)
        ok_my = self.OK_SEKME_Y + self.OK_SEKME_YUKSEKLIK / 2
        ok_mx = ok_sekme_x_pos + self.OK_SEKME_GENISLIK / 2
        pts = ([(ok_mx - 4, ok_my - 10), (ok_mx + 4, ok_my), (ok_mx - 4, ok_my + 10)] if self.kutu_acik else [(ok_mx + 4, ok_my - 10), (ok_mx - 4, ok_my), (ok_mx + 4, ok_my + 10)])
        pygame.draw.polygon(self.ekran, self.OK_RENK, pts, 3)

    def ekran_temizle(self):
        self.ekran.fill(self.CIMEN)

    def saat_tik(self, fps=60):
        self.saat.tick(fps)



