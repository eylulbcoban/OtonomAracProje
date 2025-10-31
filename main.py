import pygame
import sys
import math
from typing import List, Optional, Callable

from harita import Harita
from araba import Araba as HaritaAraba
from npc_araba import npc_arac_uret, NPCArac
from engel import (
    Engel,
    YayaGecidi,
    YolCalismasi,
    HizKesici,
    TrafikIsigi,
    en_yakin_duz_segmente_projeksiyon,
    engel_uzunlugunu_degistir,
    engel_dondur_90,
)


class Game:
    def __init__(self, genislik: int = 1500, yukseklik: int = 700):
        self.harita = Harita(genislik, yukseklik)
        self.engeller: List[Engel] = []
        self.npcs: List[NPCArac] = []
        self.secili_engel: Optional[Engel] = None
        self.surukleniyor = False
        self.suruklenen_yeni_isik: Optional[TrafikIsigi] = None

        def get_engeller() -> List[Engel]:
            return self.engeller

        def get_npcs() -> List[NPCArac]:
            return self.npcs

        araba_uzunluk = int(self.harita.YOL_KALINLIK * 0.7)
        araba_genislik = int(self.harita.YOL_KALINLIK * 0.35)
        baslangic_x, baslangic_y = self.harita.kose(2, 2)
        self.araba = HaritaAraba(self.harita, get_engeller, get_npcs, baslangic_x, baslangic_y, araba_uzunluk, araba_genislik, gorsel_yolu="mainaraba.png")

        self._ek_engelleri_baslat()
        
        # Haritayı bir kez çiz (NPC pozisyon kontrolü için)
        self.harita.ekran.fill(self.harita.CIMEN)
        for yol in self.harita.yollar:
            self.harita.yol_ciz(yol)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_1, self.harita.KAVSAK_YARICAP)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_2, self.harita.KAVSAK_YARICAP)
        
        # NPC'leri oluştur (harita çizildikten sonra)
        self.npcs = npc_arac_uret(self.harita, araba_uzunluk, araba_genislik, self.araba.x, self.araba.y, get_engeller, get_npcs)


    def _ek_engelleri_baslat(self):
        yol_k = self.harita.YOL_KALINLIK
        #Yaya geçitletri
        self.engeller.append(YayaGecidi(self.harita, self.harita.kose(4, 10), self.harita.kose(6, 10), int(yol_k * 0.8)))
        self.engeller.append(YayaGecidi(self.harita, self.harita.kose(6, 5), self.harita.kose(3, 1), int(yol_k * 0.8)))
        self.engeller.append(YayaGecidi(self.harita, self.harita.kose(15, 10), self.harita.kose(15, 12), int(yol_k * 0.8)))
        #Yol çalışması
        self.engeller.append(YolCalismasi(self.harita, self.harita.kose(10, 5), self.harita.kose(10, 7), int(yol_k * 0.8)))
        #Kasis
        self.engeller.append(HizKesici(self.harita, self.harita.kose(8, 10), self.harita.kose(9, 10), int(yol_k * 0.7)))
        self.engeller.append(HizKesici(self.harita, self.harita.kose(11, 4), self.harita.kose(12, 4), int(yol_k * 0.7)))
        #Trafik ışıkları
        self.engeller.append(TrafikIsigi(self.harita, c=5, r=6, yon='yatay'))
        self.engeller.append(TrafikIsigi(self.harita, c=9, r=2, yon='yatay'))
        self.engeller.append(TrafikIsigi(self.harita, c=15, r=8, yon='yatay'))

    def _yeni_cizgisel_engel(self, cls: Callable, mx: int, my: int, hedef_uzunluk_px: int) -> Optional[Engel]:
        sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
        if sonuc is None:
            return None
        p1, p2, (px, py), _t, ux, uy = sonuc
        yarim = hedef_uzunluk_px / 2
        a = (px - ux * yarim, py - uy * yarim)
        b = (px + ux * yarim, py + uy * yarim)
        return cls(self.harita, a, b, int(self.harita.YOL_KALINLIK * 0.75))
    
    def _yeni_yaya_gecidi(self, mx: int, my: int, hedef_uzunluk_px: int) -> Optional[Engel]:
        """Yaya geçidini yol yönüne dik olarak oluşturur (panelden ekleme için)"""
        sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
        if sonuc is None:
            return None
        p1, p2, (px, py), _t, ux, uy = sonuc
        # Yaya geçidini merkez noktası etrafında geçici olarak yerleştir
        # _yol_yonune_dik_yerlestir metodu bunu otomatik olarak düzeltecek
        yarim = hedef_uzunluk_px / 2
        # Geçici noktalar: YayaGecidi.__init__ içindeki _yol_yonune_dik_yerlestir
        # bunları yol yönüne dik olacak şekilde düzeltecek
        a = (px - yarim, py)
        b = (px + yarim, py)
        return YayaGecidi(self.harita, a, b, int(self.harita.YOL_KALINLIK * 0.75))

    def _engel_secimi(self, mx: int, my: int):
        yakin_engel = None
        yakin_mesafe = float('inf')
        for engel in self.engeller:
            if hasattr(engel, '_proj_ve_mesafe'):
                t, dik, uzunluk = engel._proj_ve_mesafe(mx, my)
                if 0 <= t <= uzunluk and dik <= max(getattr(engel, 'genislik', 0) / 2, 20):
                    if dik < yakin_mesafe:
                        yakin_mesafe = dik
                        yakin_engel = engel
            elif isinstance(engel, TrafikIsigi):
                dist = math.hypot(engel.pixel_pos[0] - mx, engel.pixel_pos[1] - my)
                if dist < self.harita.HUCRE * 1.2 and dist < yakin_mesafe:
                    yakin_mesafe = dist
                    yakin_engel = engel
        self.secili_engel = yakin_engel
        self.surukleniyor = self.secili_engel is not None

    def _kasis_etkisi(self):
        radyan = math.radians(self.araba.aci)
        kontrol_noktasi_mesafesi = self.araba.orijinal_gorsel.get_width() / 2 * 0.8
        sapma_x = kontrol_noktasi_mesafesi * math.cos(radyan)
        sapma_y = -kontrol_noktasi_mesafesi * math.sin(radyan)
        bx = self.araba.x + sapma_x
        by = self.araba.y + sapma_y
        for engel in self.engeller:
            if isinstance(engel, HizKesici) and engel.icinde_mi(bx, by):
                self.araba.hiz *= engel.carpma_orani
                break

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            if self.harita.ok_rect and self.harita.ok_rect.collidepoint((mx, my)):
                self.harita.kutu_acik = not self.harita.kutu_acik
                return
            if self.harita.kutu_acik:
                if self.harita.BTN_ADD_YAYA and self.harita.BTN_ADD_YAYA.collidepoint((mx, my)):
                    e = self._yeni_yaya_gecidi(mx, my, int(self.harita.HUCRE * 2))
                    if e:
                        self.engeller.append(e); self.secili_engel = e
                    return
                if self.harita.BTN_ADD_CALISMA and self.harita.BTN_ADD_CALISMA.collidepoint((mx, my)):
                    e = self._yeni_cizgisel_engel(YolCalismasi, mx, my, int(self.harita.HUCRE * 2))
                    if e:
                        self.engeller.append(e); self.secili_engel = e
                    return
                if self.harita.BTN_ADD_KASIS and self.harita.BTN_ADD_KASIS.collidepoint((mx, my)):
                    e = self._yeni_cizgisel_engel(HizKesici, mx, my, int(self.harita.HUCRE * 1.5))
                    if e:
                        self.engeller.append(e); self.secili_engel = e
                    return
                if self.harita.BTN_ADD_ISIK and self.harita.BTN_ADD_ISIK.collidepoint((mx, my)):
                    yeni_isik = TrafikIsigi(self.harita, c=0, r=0, yon='dikey')
                    yeni_isik.surukleniyor_ilk = True
                    yeni_isik.pixel_pos = (mx, my)
                    yeni_isik.gorsel_konumunu_guncelle()
                    self.suruklenen_yeni_isik = yeni_isik
                    self.engeller.append(yeni_isik)
                    return
                if self.harita.BTN_DELETE and self.harita.BTN_DELETE.collidepoint((mx, my)):
                    if self.secili_engel in self.engeller:
                        self.engeller.remove(self.secili_engel)
                        self.secili_engel = None
                        self.surukleniyor = False
                    return
                if self.harita.BTN_ROTATE and self.harita.BTN_ROTATE.collidepoint((mx, my)):
                    if self.secili_engel:
                        engel_dondur_90(self.harita, self.secili_engel)
                    return
                if self.harita.BTN_LONGER and self.harita.BTN_LONGER.collidepoint((mx, my)):
                    if self.secili_engel:
                        engel_uzunlugunu_degistir(self.harita, self.secili_engel, +int(self.harita.HUCRE * 0.5))
                    return
                if self.harita.BTN_SHORTER and self.harita.BTN_SHORTER.collidepoint((mx, my)):
                    if self.secili_engel:
                        engel_uzunlugunu_degistir(self.harita, self.secili_engel, -int(self.harita.HUCRE * 0.5))
                    return
            self._engel_secimi(mx, my)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.surukleniyor = False
            if self.suruklenen_yeni_isik is not None:
                mx, my = pygame.mouse.get_pos()
                sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
                if sonuc:
                    p1, p2, (px, py), _t, ux, uy = sonuc
                    yon = 'dikey' if abs(uy) > abs(ux) else 'yatay'
                    c = round((px - self.harita.KENAR_BOSLUK - self.harita.OFFSET_X) / self.harita.HUCRE)
                    r = round((py - self.harita.KENAR_BOSLUK - self.harita.OFFSET_Y) / self.harita.HUCRE)
                    self.suruklenen_yeni_isik.c, self.suruklenen_yeni_isik.r = c, r
                    self.suruklenen_yeni_isik.yon = yon
                    self.suruklenen_yeni_isik.pixel_pos = self.harita.kose(c, r)
                    self.suruklenen_yeni_isik.surukleniyor_ilk = False
                    self.suruklenen_yeni_isik.gorsel_konumunu_guncelle()
                else:
                    if self.suruklenen_yeni_isik in self.engeller:
                        self.engeller.remove(self.suruklenen_yeni_isik)
                self.suruklenen_yeni_isik = None

        if event.type == pygame.MOUSEMOTION:
            if self.surukleniyor and self.secili_engel is not None:
                mx, my = pygame.mouse.get_pos()
                if isinstance(self.secili_engel, TrafikIsigi):
                    sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
                    if sonuc:
                        p1, p2, (px, py), _t, ux, uy = sonuc
                        yon = 'dikey' if abs(uy) > abs(ux) else 'yatay'
                        c = round((px - self.harita.KENAR_BOSLUK - self.harita.OFFSET_X) / self.harita.HUCRE)
                        r = round((py - self.harita.KENAR_BOSLUK - self.harita.OFFSET_Y) / self.harita.HUCRE)
                        self.secili_engel.c = c
                        self.secili_engel.r = r
                        self.secili_engel.yon = yon
                        self.secili_engel.pixel_pos = self.harita.kose(c, r)
                        self.secili_engel.gorsel_konumunu_guncelle()
                else:
                    sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
                    if sonuc:
                        p1, p2, (px, py), _t, ux, uy = sonuc
                        # Yaya geçidi için yol yönüne dik yerleştir
                        if isinstance(self.secili_engel, YayaGecidi):
                            # Yaya geçidinin uzunluğunu yol genişliğine göre ayarla
                            yaya_gecidi_uzunlugu = self.harita.YOL_KALINLIK
                            yarim = yaya_gecidi_uzunlugu / 2
                            # Yol yönüne dik vektör (-uy, ux)
                            dik_ux = -uy
                            dik_uy = ux
                            # Geçici noktalar oluştur, sonra _yol_yonune_dik_yerlestir düzeltecek
                            gecici_p1 = (px + dik_ux * yarim, py + dik_uy * yarim)
                            gecici_p2 = (px - dik_ux * yarim, py - dik_uy * yarim)
                            self.secili_engel.p1 = gecici_p1
                            self.secili_engel.p2 = gecici_p2
                            # Yol yönüne dik yerleştir (bu metod uzunluğu zaten YOL_KALINLIK'a ayarlayacak)
                            self.secili_engel._yol_yonune_dik_yerlestir(gecici_p1, gecici_p2)
                        else:
                            # Diğer engeller yol boyunca
                            uzunluk = math.hypot(self.secili_engel.p2[0] - self.secili_engel.p1[0], self.secili_engel.p2[1] - self.secili_engel.p1[1])
                            yarim = uzunluk / 2
                            self.secili_engel.p1 = (px - ux * yarim, py - uy * yarim)
                            self.secili_engel.p2 = (px + ux * yarim, py + uy * yarim)
            elif self.suruklenen_yeni_isik is not None:
                mx, my = pygame.mouse.get_pos()
                self.suruklenen_yeni_isik.pixel_pos = (mx, my)
                self.suruklenen_yeni_isik.gorsel_konumunu_guncelle()

    def update(self):
        tuslar = pygame.key.get_pressed()
        self.araba.kontrolleri_guncelle(tuslar)
        self._kasis_etkisi()
        for npc in self.npcs:
            npc.guncelle()
        for e in self.engeller:
            if isinstance(e, TrafikIsigi):
                e.guncelle()
            elif isinstance(e, YayaGecidi):
                e.update()
        self.araba.carpismayi_kontrol_et_ve_hareket_et()

    def draw(self):
        self.harita.ekran_temizle()
        for yol in self.harita.yollar:
            self.harita.yol_ciz(yol)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_1, self.harita.KAVSAK_YARICAP)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_2, self.harita.KAVSAK_YARICAP)
        for e in self.engeller:
            e.ciz()
            if e is self.secili_engel:
                try:
                    if hasattr(e, 'p1'):
                        pygame.draw.line(self.harita.ekran, (0, 255, 255), e.p1, e.p2, 3)
                        pygame.draw.circle(self.harita.ekran, (0, 255, 255), (int(e.p1[0]), int(e.p1[1])), 6, 2)
                        pygame.draw.circle(self.harita.ekran, (0, 255, 255), (int(e.p2[0]), int(e.p2[1])), 6, 2)
                    else:
                        pygame.draw.circle(self.harita.ekran, (0, 255, 255), e.pixel_pos, 10, 3)
                except Exception:
                    pass
        for npc in self.npcs:
            # NPC'lere ana arabayı algılayabilmeleri için referans ver
            if not hasattr(npc, 'ana_araba') or npc.ana_araba is None:
                npc.ana_araba = self.araba
            npc.ciz()
        self.araba.ciz()
        self.araba.sensorleri_ciz()
        self.harita.sensor_paneli_ciz(getattr(self.araba, 'sensor_mesafeleri', [0, 0, 0]))
        self.harita.panel_ciz()
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
            self.harita.saat_tik(60)


if __name__ == "__main__":
    Game().run()

