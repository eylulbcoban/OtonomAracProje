import pygame, math


class Araba(pygame.sprite.Sprite):
    def __init__(self, harita, engeller_ref, npc_ref, x, y, genislik, yukseklik, gorsel_yolu="mainaraba.png"):
        super().__init__()
        self.h = harita
        self.get_engeller = engeller_ref
        self.get_npcs = npc_ref
        self.x = x
        self.y = y
        self.aci = 0
        self.hiz = 0
        self.maks_hiz = 2.0
        self.ivme = 0.1
        self.yavaslama = 0.05
        self.donus_hizi = 2.0
        try:
            yuklenen_gorsel = pygame.image.load(gorsel_yolu).convert_alpha()
            self.orijinal_gorsel = pygame.transform.scale(yuklenen_gorsel, (genislik, yukseklik))
        except pygame.error as e:
            print(f"Hata: Araç görseli yüklenemedi ('{gorsel_yolu}'): {e}")
            self.orijinal_gorsel = pygame.Surface([genislik, yukseklik])
            self.orijinal_gorsel.fill((220, 0, 0))
            pygame.draw.polygon(self.orijinal_gorsel, (0, 0, 0), [(genislik, yukseklik / 2), (genislik * 0.75, yukseklik * 0.25), (genislik * 0.75, yukseklik * 0.75)])
        self.image = self.orijinal_gorsel
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.sensor_mesafeleri = [0, 0, 0]

    def kontrolleri_guncelle(self, tuslar):
        if tuslar[pygame.K_UP]:
            self.hiz = min(self.hiz + self.ivme, self.maks_hiz)
        elif tuslar[pygame.K_DOWN]:
            self.hiz = max(self.hiz - self.ivme, -self.maks_hiz / 2)
        else:
            if self.hiz > 0:
                self.hiz = max(self.hiz - self.yavaslama, 0)
            elif self.hiz < 0:
                self.hiz = min(self.hiz + self.yavaslama, 0)
        if self.hiz != 0:
            if tuslar[pygame.K_LEFT]:
                self.aci += self.donus_hizi * (self.hiz / self.maks_hiz)
            if tuslar[pygame.K_RIGHT]:
                self.aci -= self.donus_hizi * (self.hiz / self.maks_hiz)

    def _renk_cimen_mi(self, renk):
        """Renk çimen rengi mi kontrol eder (0 tolerans - tam eşleşme)"""
        if len(renk) < 3:
            return False
        # Çimen rengi (RGB veya RGBA formatında olabilir)
        c_r, c_g, c_b = self.h.CIMEN[:3]
        # Gelen renk (RGBA formatında olabilir, sadece RGB kısmını al)
        r_r, r_g, r_b = renk[0], renk[1], renk[2]
        # Tam eşleşme kontrolü (0 tolerans - kesinlikle çimen rengi olmalı)
        return (c_r == r_r and c_g == r_g and c_b == r_b)
    
    def carpismayi_kontrol_et_ve_hareket_et(self):
        ekran = self.h.ekran
        radyan = math.radians(self.aci)
        yeni_x = self.x + self.hiz * math.cos(radyan)
        yeni_y = self.y - self.hiz * math.sin(radyan)
        
        # Arabanın önünde ve kenarlarında birden fazla nokta kontrol et
        araba_genislik = self.orijinal_gorsel.get_width()
        araba_yukseklik = self.orijinal_gorsel.get_height()
        
        if self.hiz >= 0:
            kontrol_noktasi_mesafesi = araba_genislik / 2 * 0.9
        else:
            kontrol_noktasi_mesafesi = -araba_genislik / 2 * 0.9
        
        # Arabanın ön kenarı boyunca çoklu kontrol noktaları
        kontrol_noktalari = []
        sapma_x = kontrol_noktasi_mesafesi * math.cos(radyan)
        sapma_y = -kontrol_noktasi_mesafesi * math.sin(radyan)
        
        # Araç önü boyunca 5 nokta kontrol et (sol kenar, sol-orta, merkez, sağ-orta, sağ kenar)
        yan_nokta_sayisi = 5
        yan_sapma_max = araba_yukseklik / 2 * 0.8  # Araç genişliğinin tam kenarı
        
        for i in range(yan_nokta_sayisi):
            # -1.0'den +1.0'e kadar normalize pozisyon
            yan_oran = -1.0 + (i / (yan_nokta_sayisi - 1)) * 2.0
            yan_sapma = yan_sapma_max * yan_oran
            
            # Yan sapmayı araç açısına göre hesapla
            yan_sapma_x = -yan_sapma * math.sin(radyan)
            yan_sapma_y = -yan_sapma * math.cos(radyan)
            
            kontrol_x = yeni_x + sapma_x + yan_sapma_x
            kontrol_y = yeni_y + sapma_y + yan_sapma_y
            kontrol_noktalari.append((kontrol_x, kontrol_y))
        
        guvenli_mi = True
        try:
            # Her kontrol noktasını kontrol et
            for kontrol_x, kontrol_y in kontrol_noktalari:
                # Ekran sınırları kontrolü
                if not (0 <= int(kontrol_x) < self.h.GENISLIK and 0 <= int(kontrol_y) < self.h.YUKSEKLIK):
                    guvenli_mi = False
                    break
                
                # Çimen rengi kontrolü (0 tolerans - kesin)
                kontrol_renk = ekran.get_at((int(kontrol_x), int(kontrol_y)))
                if self._renk_cimen_mi(kontrol_renk):
                    guvenli_mi = False
                    break
                
                # Engelleri kontrol et
                for engel in self.get_engeller():
                    if engel.carpisti_mi(kontrol_x, kontrol_y):
                        from engel import TrafikIsigi
                        if isinstance(engel, TrafikIsigi) and getattr(engel, 'durum', None) == "kirmizi":
                            guvenli_mi = False
                            break
                        elif not isinstance(engel, TrafikIsigi):
                            guvenli_mi = False
                            break
                    if not guvenli_mi:
                        break
                
                if not guvenli_mi:
                    break
                
                # NPC araçlarını kontrol et
                for npc in self.get_npcs():
                    npc_mesafe = math.hypot(npc.x - kontrol_x, npc.y - kontrol_y)
                    guvenli_mesafe = (araba_genislik + npc.orijinal_gorsel.get_width()) / 2 + 10
                    if npc_mesafe < guvenli_mesafe:
                        guvenli_mi = False
                        break
                
                if not guvenli_mi:
                    break
        except (IndexError, ValueError):
            guvenli_mi = False
        
        if guvenli_mi:
            self.x = yeni_x
            self.y = yeni_y
        else:
            self.hiz = 0
        self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def ciz(self):
        self.h.ekran.blit(self.image, self.rect)

    def sensorleri_ciz(self):
        ekran = self.h.ekran
        sensor_acilari = [-45, 0, 45]
        max_mesafe = 250
        self.sensor_mesafeleri = []
        for aci_deg in sensor_acilari:
            toplam_aci = math.radians(self.aci - aci_deg)
            carpti_mi = False
            uzaklik = 0
            renk_cizgi = (0, 255, 0)
            for uzaklik in range(0, max_mesafe, 5):
                x = int(self.x + math.cos(toplam_aci) * uzaklik)
                y = int(self.y - math.sin(toplam_aci) * uzaklik)
                if not (0 <= x < self.h.GENISLIK and 0 <= y < self.h.YUKSEKLIK):
                    break
                renk = ekran.get_at((x, y))
                carpti_mi = False
                if self._renk_cimen_mi(renk):
                    carpti_mi = True
                else:
                    for engel in self.get_engeller():
                        if engel.carpisti_mi(x, y):
                            carpti_mi = True
                            break
                    if not carpti_mi:
                        for npc in self.get_npcs():
                            npc_mesafe = math.hypot(npc.x - x, npc.y - y)
                            algilama_mesafe = (self.orijinal_gorsel.get_width() + npc.orijinal_gorsel.get_width()) / 2 + 15
                            if npc_mesafe < algilama_mesafe:
                                carpti_mi = True
                                break
                if carpti_mi:
                    break
            if uzaklik < 40:
                renk_cizgi = (255, 0, 0)
            elif uzaklik < 80:
                renk_cizgi = (255, 255, 0)
            else:
                renk_cizgi = (0, 255, 0)
            x = int(self.x + math.cos(toplam_aci) * uzaklik)
            y = int(self.y - math.sin(toplam_aci) * uzaklik)
            pygame.draw.line(ekran, renk_cizgi, (self.x, self.y), (x, y), 2)
            pygame.draw.circle(ekran, renk_cizgi, (x, y), 4)
            self.sensor_mesafeleri.append(uzaklik)



