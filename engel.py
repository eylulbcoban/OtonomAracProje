import pygame, math, random


class Engel:
    def ciz(self):
        pass

    def carpisti_mi(self, x, y):
        return False


class YayaGecidi(Engel):
    _tum_yaya_gorselleri = []

    def __init__(self, harita, p1, p2, genislik):
        self.h = harita
        self.genislik = genislik
        self.cizgi_genislik = max(6, int(self.genislik * 0.12))
        self.bosluk = self.cizgi_genislik

        self.yayalar_aktif_mi = False
        self.aktif_sure = 5000
        self.pasif_sure = 8000
        self.son_degisim_zamani = pygame.time.get_ticks() + 3000

        self.yaya_hiz = 0.3
        self.yaya_konumlari = []
        self.yaya_yonleri = []
        self.yaya_sayisi = 3
        self.yaya_aralik = 0.3
        self.yaya_bekleme_suresi = 0

        if not YayaGecidi._tum_yaya_gorselleri:
            try:
                tam_gorsel_seti = pygame.image.load("yaya2.png").convert_alpha()
                yaya_genislik = tam_gorsel_seti.get_width() // 5
                yaya_yukseklik = tam_gorsel_seti.get_height() // 5
                for row in range(3):
                    for col in range(3):
                        yaya_rect = pygame.Rect(col * yaya_genislik, row * yaya_yukseklik, yaya_genislik, yaya_yukseklik)
                        tek_yaya = pygame.Surface(yaya_rect.size, pygame.SRCALPHA)
                        tek_yaya.blit(tam_gorsel_seti, (0, 0), yaya_rect)
                        YayaGecidi._tum_yaya_gorselleri.append(pygame.transform.scale(tek_yaya, (20, 20)))
            except pygame.error:
                print("Uyarı: 'yaya2.png' dosyası bulunamadı. Yayalar daire olarak çizilecek.")

        self.secilen_yaya_orijinal = random.choice(YayaGecidi._tum_yaya_gorselleri) if YayaGecidi._tum_yaya_gorselleri else None
        self.yaya_gorsel_1 = None
        self.yaya_gorsel_2 = None

        # Yaya geçidini yol yönüne dik olarak yerleştir
        self._yol_yonune_dik_yerlestir(p1, p2)

    def _yol_yonune_dik_yerlestir(self, p1_orijinal, p2_orijinal):
        """Yaya geçidini yol yönüne dik olacak şekilde yerleştirir"""
        # Merkez noktasını hesapla
        merkez_x = (p1_orijinal[0] + p2_orijinal[0]) / 2
        merkez_y = (p1_orijinal[1] + p2_orijinal[1]) / 2
        
        # En yakın yol segmentini bul - manuel hesapla (döngüsel import'tan kaçınmak için)
        dogrular = []
        for seg in self.h.yollar:
            for i in range(len(seg) - 1):
                p1, p2 = seg[i], seg[i + 1]
                if p1[0] == p2[0] or p1[1] == p2[1]:
                    dogrular.append((p1, p2))
        
        en_iyi = None
        en_kucuk = float('inf')
        for yol_p1, yol_p2 in dogrular:
            (x1, y1), (x2, y2) = yol_p1, yol_p2
            vx, vy = (x2 - x1), (y2 - y1)
            uzunluk = math.hypot(vx, vy)
            if uzunluk == 0:
                continue
            ux, uy = vx / uzunluk, vy / uzunluk
            wx, wy = merkez_x - x1, merkez_y - y1
            t = max(0, min(uzunluk, wx * ux + wy * uy))
            px = x1 + ux * t
            py = y1 + uy * t
            dik = abs(wx * (-uy) + wy * ux)
            if dik < en_kucuk:
                en_kucuk = dik
                en_iyi = (yol_p1, yol_p2, (px, py), t, ux, uy)
        sonuc = en_iyi
        
        if sonuc is None:
            # Yol bulunamadıysa, orijinal noktaları kullan
            self.p1 = p1_orijinal
            self.p2 = p2_orijinal
        else:
            # Yol segmentinin yönünü al
            yol_p1, yol_p2, (proj_x, proj_y), _t, ux, uy = sonuc
            
            # Yol yönüne dik vektör hesapla (-uy, ux)
            dik_ux = -uy
            dik_uy = ux
            
            # Yaya geçidinin uzunluğunu yol genişliğine göre ayarla
            # Yaya geçidi yolun enine (genişliğine) tam olarak uymalı
            yaya_gecidi_uzunlugu = self.h.YOL_KALINLIK
            yarim = yaya_gecidi_uzunlugu / 2
            
            # Yaya geçidini dik vektör boyunca yerleştir
            self.p1 = (proj_x + dik_ux * yarim, proj_y + dik_uy * yarim)
            self.p2 = (proj_x - dik_ux * yarim, proj_y - dik_uy * yarim)
        
        # Yaya yönünü hesapla (yayalar yaya geçidi boyunca hareket eder)
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk > 0:
            # Yayalar yaya geçidi boyunca hareket eder
            self.yaya_aci = math.degrees(math.atan2(-vy, vx))
        else:
            self.yaya_aci = 0
        
        if self.secilen_yaya_orijinal:
            self.yaya_gorsel_1 = pygame.transform.rotate(self.secilen_yaya_orijinal, self.yaya_aci)
            self.yaya_gorsel_2 = pygame.transform.rotate(self.secilen_yaya_orijinal, self.yaya_aci + 180)

    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def update(self):
        simdiki_zaman = pygame.time.get_ticks()
        if self.yayalar_aktif_mi:
            if simdiki_zaman - self.son_degisim_zamani > self.aktif_sure:
                self.yayalar_aktif_mi = False
                self.son_degisim_zamani = simdiki_zaman
                self.yaya_konumlari = []
                self.yaya_yonleri = []
        else:
            if simdiki_zaman - self.son_degisim_zamani > self.pasif_sure:
                self.yayalar_aktif_mi = True
                self.son_degisim_zamani = simdiki_zaman
                self.yaya_konumlari = [0.0]
                self.yaya_yonleri = [True]
        if self.yayalar_aktif_mi:
            self._yayalari_hareket_ettir()

    def _yayalari_hareket_ettir(self):
        if not self.yaya_konumlari:
            return
        for i in range(len(self.yaya_konumlari) - 1, -1, -1):
            if self.yaya_yonleri[i]:
                self.yaya_konumlari[i] += self.yaya_hiz / self.genislik
                if self.yaya_konumlari[i] >= 1.0:
                    self.yaya_konumlari.pop(i)
                    self.yaya_yonleri.pop(i)
            else:
                self.yaya_konumlari[i] -= self.yaya_hiz / self.genislik
                if self.yaya_konumlari[i] <= 0.0:
                    self.yaya_konumlari.pop(i)
                    self.yaya_yonleri.pop(i)
        if len(self.yaya_konumlari) < self.yaya_sayisi:
            self.yaya_bekleme_suresi -= 1
            if self.yaya_bekleme_suresi <= 0:
                if random.random() < 0.02:
                    baslangic_tarafi = random.choice([True, False])
                    yeni_konum = 0.0 if baslangic_tarafi else 1.0
                    yeni_yon = baslangic_tarafi
                    yeterince_uzak = True
                    for mevcut_konum in self.yaya_konumlari:
                        if abs(mevcut_konum - yeni_konum) < self.yaya_aralik:
                            yeterince_uzak = False
                            break
                    if yeterince_uzak:
                        self.yaya_konumlari.append(yeni_konum)
                        self.yaya_yonleri.append(yeni_yon)
                        self.yaya_bekleme_suresi = random.randint(30, 120)

    def carpisti_mi(self, x, y):
        if not self.yayalar_aktif_mi:
            return False
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        if 0 <= t <= uzunluk and dik <= self.genislik / 2:
            return True
        return False

    def ciz(self):
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return
        ux, uy = vx / uzunluk, vy / uzunluk
        px, py = -uy, ux
        t = 0
        while t <= uzunluk:
            cx = x1 + ux * t
            cy = y1 + uy * t
            yarim = self.genislik / 2
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            pygame.draw.line(ekran, (255, 255, 255), a, b, self.cizgi_genislik)
            t += self.cizgi_genislik + self.bosluk
        if self.yayalar_aktif_mi and self.yaya_konumlari:
            yaya_rengi_fallback = (220, 50, 50)
            yaya_yaricap_fallback = 7
            yanal_konumlar = [self.genislik * -0.3, 0, self.genislik * 0.3]
            for i, (yaya_konum, yaya_yon) in enumerate(zip(self.yaya_konumlari, self.yaya_yonleri)):
                t = uzunluk * yaya_konum
                yanal_index = i % len(yanal_konumlar)
                kaydirma = yanal_konumlar[yanal_index]
                cx = int(x1 + ux * t + px * kaydirma)
                cy = int(y1 + uy * t + py * kaydirma)
                if self.yaya_gorsel_1:
                    g = self.yaya_gorsel_1 if yaya_yon else self.yaya_gorsel_2
                    rect = g.get_rect(center=(cx, cy))
                    ekran.blit(g, rect)
                else:
                    pygame.draw.circle(ekran, yaya_rengi_fallback, (cx, cy), yaya_yaricap_fallback)
                    pygame.draw.circle(ekran, (0, 0, 0), (cx, cy), yaya_yaricap_fallback, 2)


class YolCalismasi(Engel):
    def __init__(self, harita, p1, p2, genislik):
        self.h = harita
        self.p1 = p1
        self.p2 = p2
        self.genislik = genislik

    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def carpisti_mi(self, x, y):
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        return (0 <= t <= uzunluk) and (dik <= self.genislik / 2)

    def ciz(self):
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return
        ux, uy = vx / uzunluk, vy / uzunluk
        px, py = -uy, ux
        yarim = self.genislik / 2
        adim = max(8, int(self.genislik * 0.18))
        t = 0
        while t <= uzunluk:
            cx = x1 + ux * t
            cy = y1 + uy * t
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            renk = (255, 140, 0) if (int(t / adim) % 2 == 0) else (230, 120, 0)
            pygame.draw.line(ekran, renk, a, b, max(6, int(self.genislik * 0.6)))
            t += adim


class HizKesici(Engel):
    def __init__(self, harita, p1, p2, genislik, carpma_orani=0.6):
        self.h = harita
        self.p1 = p1
        self.p2 = p2
        self.genislik = genislik
        self.carpma_orani = carpma_orani

    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def icinde_mi(self, x, y):
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        return (0 <= t <= uzunluk) and (dik <= self.genislik / 2)

    def carpisti_mi(self, x, y):
        return False

    def ciz(self):
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        L = math.hypot(vx, vy)
        if L == 0:
            return
        ux, uy = vx / L, vy / L
        px, py = -uy, ux
        yarim = self.genislik / 2
        cizgi = max(6, int(self.genislik * 0.18))
        aralik = cizgi
        t = 0
        renkler = [(255, 210, 0), (60, 60, 60)]
        i = 0
        while t <= L:
            cx = x1 + ux * t
            cy = y1 + uy * t
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            pygame.draw.line(ekran, renkler[i % 2], a, b, cizgi)
            t += aralik
            i += 1


class TrafikIsigi(Engel):
    def __init__(self, harita, c=0, r=0, yon='dikey', baslangic_durumu="kirmizi", kirmizi_sure_sn=7, yesil_sure_sn=5, sari_sure_sn=2):
        self.h = harita
        self.c, self.r = c, r
        self.pixel_pos = self.h.kose(c, r)
        self.yon = yon
        self.tip = "isik"
        self.lamba_yaricap = int(self.h.HUCRE * 0.1) if self.h.HUCRE > 0 else 5
        self.surukleniyor_ilk = False
        self.kutu_rect = pygame.Rect(0, 0, 0, 0)
        self.kutu_genislik = 0
        self.kutu_yukseklik = 0
        self.kirmizi_pos = (0, 0)
        self.sari_pos = (0, 0)
        self.yesil_pos = (0, 0)
        self.stop_line_p1 = (0, 0)
        self.stop_line_p2 = (0, 0)
        self.gorsel_konumunu_guncelle()
        self.durum = baslangic_durumu
        self.kirmizi_sure = kirmizi_sure_sn * 60
        self.yesil_sure = yesil_sure_sn * 60
        self.sari_sure = sari_sure_sn * 60
        if self.durum == "kirmizi":
            self.zamanlayici = self.kirmizi_sure
        elif self.durum == "yesil":
            self.zamanlayici = self.yesil_sure
        else:
            self.zamanlayici = self.sari_sure

    def gorsel_konumunu_guncelle(self):
        lamba_araligi = self.lamba_yaricap * 2.5
        is_dikey_kutu = self.yon == 'yatay' or self.surukleniyor_ilk
        if self.surukleniyor_ilk:
            self.pixel_pos = pygame.mouse.get_pos()
        if is_dikey_kutu:
            self.kutu_genislik = self.lamba_yaricap * 2 + int(self.lamba_yaricap * 0.5)
            self.kutu_yukseklik = (self.lamba_yaricap * 6) + (self.lamba_yaricap * 2)
            offset_y = 0 if self.surukleniyor_ilk else -(self.h.YOL_KALINLIK / 2 + self.kutu_yukseklik / 2 + 5)
            offset_x = 0
        else:
            self.kutu_genislik = (self.lamba_yaricap * 6) + (self.lamba_yaricap * 2)
            self.kutu_yukseklik = self.lamba_yaricap * 2 + int(self.lamba_yaricap * 0.5)
            offset_y = -(self.h.YOL_KALINLIK / 2 + self.kutu_yukseklik / 2 + 5)
            offset_x = 0
        self.kutu_rect = pygame.Rect(self.pixel_pos[0] + offset_x - self.kutu_genislik / 2, self.pixel_pos[1] + offset_y - self.kutu_yukseklik / 2, self.kutu_genislik, self.kutu_yukseklik)
        if is_dikey_kutu:
            mx = self.kutu_rect.centerx
            self.kirmizi_pos = (mx, self.kutu_rect.top + lamba_araligi)
            self.sari_pos = (mx, self.kirmizi_pos[1] + lamba_araligi)
            self.yesil_pos = (mx, self.sari_pos[1] + lamba_araligi)
        else:
            my = self.kutu_rect.centery
            self.kirmizi_pos = (self.kutu_rect.left + lamba_araligi, my)
            self.sari_pos = (self.kirmizi_pos[0] + lamba_araligi, my)
            self.yesil_pos = (self.sari_pos[0] + lamba_araligi, my)
        if not self.surukleniyor_ilk:
            yr = self.h.YOL_KALINLIK / 2
            if self.yon == 'dikey':
                self.stop_line_p1 = (self.pixel_pos[0] - yr, self.pixel_pos[1])
                self.stop_line_p2 = (self.pixel_pos[0] + yr, self.pixel_pos[1])
            else:
                self.stop_line_p1 = (self.pixel_pos[0], self.pixel_pos[1] - yr)
                self.stop_line_p2 = (self.pixel_pos[0], self.pixel_pos[1] + yr)
            px, py = self.pixel_pos
            ux, uy = (0, 1) if self.yon == 'dikey' else (1, 0)
            self.p1 = (px - ux * 1, py - uy * 1)
            self.p2 = (px + ux * 1, py + uy * 1)

    def guncelle(self):
        if self.surukleniyor_ilk:
            self.gorsel_konumunu_guncelle()
            return
        self.zamanlayici -= 1
        if self.zamanlayici <= 0:
            if self.durum == "kirmizi":
                self.durum = "yesil"; self.zamanlayici = self.yesil_sure
            elif self.durum == "yesil":
                self.durum = "sari"; self.zamanlayici = self.sari_sure
            elif self.durum == "sari":
                self.durum = "kirmizi"; self.zamanlayici = self.kirmizi_sure

    def ciz(self):
        ekran = self.h.ekran
        if not self.surukleniyor_ilk and (self.durum == "kirmizi" or self.durum == "sari"):
            try:
                pygame.draw.line(ekran, self.h.STOP_LINE_RENK, (int(self.stop_line_p1[0]), int(self.stop_line_p1[1])), (int(self.stop_line_p2[0]), int(self.stop_line_p2[1])), 4)
            except TypeError:
                pass
        pygame.draw.rect(ekran, self.h.ISIK_KUTU, self.kutu_rect, border_radius=5)
        k, s, y = self.h.KAPALI_KIRMIZI, self.h.KAPALI_SARI, self.h.KAPALI_YESIL
        if self.durum == "kirmizi":
            k = self.h.ACIK_KIRMIZI
        elif self.durum == "sari":
            s = self.h.ACIK_SARI
        elif self.durum == "yesil":
            y = self.h.ACIK_YESIL
        pygame.draw.circle(ekran, k, (int(self.kirmizi_pos[0]), int(self.kirmizi_pos[1])), int(self.lamba_yaricap))
        pygame.draw.circle(ekran, s, (int(self.sari_pos[0]), int(self.sari_pos[1])), int(self.lamba_yaricap))
        pygame.draw.circle(ekran, y, (int(self.yesil_pos[0]), int(self.yesil_pos[1])), int(self.lamba_yaricap))

    def carpisti_mi(self, x, y):
        return math.hypot(self.pixel_pos[0] - x, self.pixel_pos[1] - y) < self.h.HUCRE * 0.6


# Yardımcı projeksiyon fonksiyonları
def yol_dogrularini_cikar(yollar_listesi):
    alt = []
    for seg in yollar_listesi:
        for i in range(len(seg) - 1):
            p1, p2 = seg[i], seg[i + 1]
            if p1[0] == p2[0] or p1[1] == p2[1]:
                alt.append((p1, p2))
    return alt


def projeksiyon_ve_yakin_dik_mesafe(p1, p2, x, y):
    (x1, y1), (x2, y2) = p1, p2
    vx, vy = (x2 - x1), (y2 - y1)
    uzunluk = math.hypot(vx, vy)
    if uzunluk == 0:
        return (x1, y1), float('inf'), 0, 0, 0
    ux, uy = vx / uzunluk, vy / uzunluk
    wx, wy = x - x1, y - y1
    t = max(0, min(uzunluk, wx * ux + wy * uy))
    px = x1 + ux * t
    py = y1 + uy * t
    dik = abs(wx * (-uy) + wy * ux)
    return (px, py), dik, t, ux, uy


def en_yakin_duz_segmente_projeksiyon(harita, x, y):
    dogrular = yol_dogrularini_cikar(harita.yollar)
    en_iyi = None
    en_kucuk = float('inf')
    for p1, p2 in dogrular:
        (px, py), dik, t, ux, uy = projeksiyon_ve_yakin_dik_mesafe(p1, p2, x, y)
        if dik < en_kucuk:
            en_kucuk = dik
            en_iyi = (p1, p2, (px, py), t, ux, uy)
    return en_iyi


def engel_uzunlugunu_degistir(harita, engel, delta_px):
    if isinstance(engel, TrafikIsigi):
        if delta_px > 0:
            engel.yesil_sure = min(engel.yesil_sure + 60, 600)
        else:
            engel.yesil_sure = max(engel.yesil_sure - 60, 60)
        if engel.durum == "yesil":
            engel.zamanlayici = engel.yesil_sure
    else:
        merkez = ((engel.p1[0] + engel.p2[0]) / 2, (engel.p1[1] + engel.p2[1]) / 2)
        mevcut_uzunluk = math.hypot(engel.p2[0] - engel.p1[0], engel.p2[1] - engel.p1[1])
        yeni_uzunluk = max(20, mevcut_uzunluk + delta_px)
        sonuc = en_yakin_duz_segmente_projeksiyon(harita, *merkez)
        if sonuc is None:
            return
        p1, p2, (px, py), _t, ux, uy = sonuc
        yarim = yeni_uzunluk / 2
        engel.p1 = (px - ux * yarim, py - uy * yarim)
        engel.p2 = (px + ux * yarim, py + uy * yarim)


def engel_dondur_90(harita, engel):
    if isinstance(engel, TrafikIsigi):
        engel.yon = 'yatay' if engel.yon == 'dikey' else 'dikey'
        engel.gorsel_konumunu_guncelle()
    else:
        merkez = ((engel.p1[0] + engel.p2[0]) / 2, (engel.p1[1] + engel.p2[1]) / 2)
        uzunluk = math.hypot(engel.p2[0] - engel.p1[0], engel.p2[1] - engel.p1[1])
        sonuc = en_yakin_duz_segmente_projeksiyon(harita, *merkez)
        if sonuc is None:
            return
        _sp1, _sp2, (px, py), _t, ux, uy = sonuc
        rux, ruy = -uy, ux
        yarim = uzunluk / 2
        engel.p1 = (px - rux * yarim, py - ruy * yarim)
        engel.p2 = (px + rux * yarim, py + ruy * yarim)



