import pygame, math, random
from collections import deque
import heapq


class NPCArac(pygame.sprite.Sprite):
    def __init__(self, harita, x, y, genislik, yukseklik, yol_baslangic, yol_bitis, yol_genislik=None, resim_yolu=None, yedek_renk=(0, 0, 255), engeller_ref=None, npc_ref=None):
        super().__init__()
        self.h = harita
        self.x = x
        self.y = y
        self.get_engeller = engeller_ref if engeller_ref else (lambda: [])
        self.get_npcs = npc_ref if npc_ref else (lambda: [])
        
        # A* ve otonom hareket için değişkenler
        self.sensor_mesafeleri = [0, 0, 0]  # Sol, ön, sağ sensör mesafeleri
        self.otonom_mod = True  # Otonom hareket modu
        self.hedef_rota = []  # A* ile bulunan rota
        self.aktif_hedef_index = 0  # Rota üzerindeki mevcut hedef
        self.son_rota_guncelleme = 0  # Son rota güncelleme zamanı
        self.rota_guncelleme_araligi = 120  # Rota güncelleme aralığı (frame) - daha sık güncelle
        self.minimum_hiz = 0.5  # Minimum hız garantisi (hiç durmaması için)
        self.sag_taraf_offset = self.h.YOL_KALINLIK * 0.35  # Yolun sağ tarafına offset (trafik kuralları)
        self.serit_offset_hedef = self.h.YOL_KALINLIK * 0.35  # Hedef şerit offset (sağ şerit)
        self.serit_toleransi = self.h.YOL_KALINLIK * 0.1  # Şerit toleransı (ne kadar sapabilir)
        self.rastgele_hedef_sayaci = 0  # Rastgele hedef seçimi için sayaç
        self.guvenli_mesafe = self.h.YOL_KALINLIK * 1.5  # Öndeki araçla güvenli mesafe
        self.ana_araba_guvenli_mesafe = self.h.YOL_KALINLIK * 2.0  # Ana arabayla güvenli mesafe (daha fazla)
        try:
            if resim_yolu:
                img = pygame.image.load(resim_yolu).convert_alpha()
                self.orijinal_gorsel = pygame.transform.scale(img, (genislik, yukseklik))
            else:
                raise pygame.error("no-image")
        except pygame.error:
            self.orijinal_gorsel = pygame.Surface([genislik, yukseklik], pygame.SRCALPHA)
            self.orijinal_gorsel.fill(yedek_renk)
            pygame.draw.polygon(self.orijinal_gorsel, (255, 255, 255), [(genislik, yukseklik / 2), (genislik * 0.8, yukseklik * 0.2), (genislik * 0.8, yukseklik * 0.8)])
        self.image = self.orijinal_gorsel
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.yol_baslangic = yol_baslangic
        self.yol_bitis = yol_bitis
        self.ileri_yon = True
        dx = yol_bitis[0] - yol_baslangic[0]
        dy = yol_bitis[1] - yol_baslangic[1]
        self.yol_uzunlugu = math.hypot(dx, dy)
        self.yol_genislik = yol_genislik if yol_genislik else self.h.YOL_KALINLIK
        self.aci = -math.degrees(math.atan2(dy, dx))
        if self.yol_uzunlugu < self.h.HUCRE * 3:
            self.maks_hiz = random.uniform(1.0, 1.5)
        elif self.yol_uzunlugu < self.h.HUCRE * 6:
            self.maks_hiz = random.uniform(1.5, 2.0)
        else:
            self.maks_hiz = random.uniform(2.0, 3.0)
        self.hiz = self.maks_hiz
        self.hedef_toleransi = max(15, min(35, self.yol_genislik * 0.3))
        self.durma_modu = False
        self.durma_suresi = 0
        if self.yol_uzunlugu < self.h.HUCRE * 3:
            self.maks_durma_suresi = random.randint(90, 150)
        elif self.yol_uzunlugu < self.h.HUCRE * 6:
            self.maks_durma_suresi = random.randint(60, 120)
        else:
            self.maks_durma_suresi = random.randint(30, 90)

    def _piksel_den_hucresine(self, x, y):
        """Piksel koordinatını hücre koordinatına çevirir"""
        c = round((x - self.h.KENAR_BOSLUK - self.h.OFFSET_X) / self.h.HUCRE)
        r = round((y - self.h.KENAR_BOSLUK - self.h.OFFSET_Y) / self.h.HUCRE)
        return (c, r)
    
    def _hucresinden_piksele(self, c, r):
        """Hücre koordinatını piksel koordinatına çevirir"""
        return self.h.kose(c, r)
    
    def _yolun_sag_tarafina_offset_ekle(self, p1, p2, offset):
        """Yolun sağ tarafına offset ekler (trafik kuralları)"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        uzunluk = math.hypot(dx, dy)
        if uzunluk == 0:
            return p1
        
        # Yol yönü vektörü
        ux, uy = dx / uzunluk, dy / uzunluk
        
        # Sağ taraf vektörü (yol yönüne göre 90 derece sağa)
        # Sağ taraf = yol yönünün saat yönünde 90 derece döndürülmüş hali
        sag_x = uy * offset  # Sağa dönüş: (ux, uy) -> (uy, -ux)
        sag_y = -ux * offset
        
        # Orta noktaya sağ taraf offset'i ekle
        orta_x = (p1[0] + p2[0]) / 2
        orta_y = (p1[1] + p2[1]) / 2
        
        return (orta_x + sag_x, orta_y + sag_y)
    
    def _en_yakin_yol_segmentini_bul(self, x, y):
        """Aracın üzerinde olduğu en yakın yol segmentini bulur"""
        en_yakin_segment = None
        en_kucuk_dik_mesafe = float('inf')
        
        for yol_seg in self.h.yollar:
            for i in range(len(yol_seg) - 1):
                p1 = yol_seg[i]
                p2 = yol_seg[i + 1]
                
                # Segment vektörü
                seg_dx = p2[0] - p1[0]
                seg_dy = p2[1] - p1[1]
                seg_uzunluk = math.hypot(seg_dx, seg_dy)
                if seg_uzunluk == 0:
                    continue
                
                ux, uy = seg_dx / seg_uzunluk, seg_dy / seg_uzunluk
                
                # Noktanın segment başlangıcına göre konumu
                wx = x - p1[0]
                wy = y - p1[1]
                
                # Segment üzerindeki projeksiyon
                t = wx * ux + wy * uy
                
                # Segment üzerinde mi?
                if 0 <= t <= seg_uzunluk:
                    # Dik mesafe
                    dik_mesafe = abs(wx * (-uy) + wy * ux)
                    
                    # Yol genişliği içinde mi?
                    if dik_mesafe <= self.h.YOL_KALINLIK / 2 + 20:
                        if dik_mesafe < en_kucuk_dik_mesafe:
                            en_kucuk_dik_mesafe = dik_mesafe
                            en_yakin_segment = (p1, p2, ux, uy, t, seg_uzunluk)
        
        return en_yakin_segment
    
    def _sag_seritte_kal(self):
        """Aracın yolun sağ şeridinde kalmasını sağlar"""
        segment = self._en_yakin_yol_segmentini_bul(self.x, self.y)
        if segment is None:
            return  # Yol bulunamadı, normal devam et
        
        p1, p2, ux, uy, t, seg_uzunluk = segment
        
        # Yol merkezindeki nokta
        yol_merkez_x = p1[0] + ux * t
        yol_merkez_y = p1[1] + uy * t
        
        # Mevcut pozisyonun yol merkezinden sapması
        sapma_dx = self.x - yol_merkez_x
        sapma_dy = self.y - yol_merkez_y
        
        # Sağ taraf vektörü (yol yönüne göre 90 derece sağa)
        sag_ux = uy
        sag_uy = -ux
        
        # Sapmanın sağ taraf vektörüne göre projeksiyonu
        sag_projeksiyon = sapma_dx * sag_ux + sapma_dy * sag_uy
        
        # Hedef şerit offset'i (sağ şerit)
        hedef_offset = self.serit_offset_hedef
        
        # Sapma ne kadar?
        sapma_fark = sag_projeksiyon - hedef_offset
        
        # Eğer hedef şeritten sapmışsa düzelt
        if abs(sapma_fark) > self.serit_toleransi:
            # Şeride geri dönmek için kuvvet uygula (yumuşak düzeltme)
            duzeltme_kuvveti = -sapma_fark * 0.15  # Yumuşak düzeltme
            
            # Yeni pozisyonu hesapla (yol merkezinden hedef offset'e)
            hedef_x = yol_merkez_x + sag_ux * hedef_offset
            hedef_y = yol_merkez_y + sag_uy * hedef_offset
            
            # Mevcut pozisyondan hedefe doğru yumuşak hareket
            dx = hedef_x - self.x
            dy = hedef_y - self.y
            mesafe = math.hypot(dx, dy)
            
            if mesafe > 1:
                # Yumuşak düzeltme (çok hızlı olmasın)
                self.x += dx * 0.1
                self.y += dy * 0.1
    
    def _rastgele_hedef_sec(self):
        """Rastgele bir hedef seçer (sonsuz döngü için)"""
        if not self.h.yollar:
            return None
        
        # Rastgele bir yol seç
        rastgele_yol = random.choice(self.h.yollar)
        if len(rastgele_yol) < 2:
            return None
        
        # Rastgele bir nokta seç (başlangıç veya bitiş)
        if random.random() < 0.5:
            return rastgele_yol[0]
        else:
            return rastgele_yol[-1]
    
    def _heuristic(self, hucre1, hucre2):
        """Heuristik fonksiyon (Manhattan distance)"""
        return abs(hucre1[0] - hucre2[0]) + abs(hucre1[1] - hucre2[1])
    
    def _hucre_guvenli_mi(self, hucre):
        """Bir hücrenin güvenli olup olmadığını kontrol eder (engeller, yeşil alan)"""
        x, y = self._hucresinden_piksele(hucre[0], hucre[1])
        
        # Ekran sınırları
        if not (0 <= int(x) < self.h.GENISLIK and 0 <= int(y) < self.h.YUKSEKLIK):
            return False
        
        # Yeşil alan kontrolü
        try:
            renk = self.h.ekran.get_at((int(x), int(y)))
            if self._renk_cimen_mi(renk):
                return False
        except (IndexError, ValueError):
            return False
        
        # Engel kontrolü
        for engel in self.get_engeller():
            from engel import YolCalismasi, YayaGecidi, TrafikIsigi
            # Yol çalışması - engel
            if isinstance(engel, YolCalismasi):
                if engel.carpisti_mi(x, y):
                    return False
            # Trafik ışığı - kırmızıysa engel
            elif isinstance(engel, TrafikIsigi):
                if engel.carpisti_mi(x, y) and getattr(engel, 'durum', None) == "kirmizi":
                    return False
            # Diğer engeller
            elif engel.carpisti_mi(x, y):
                return False
        
        return True
    
    def _astar_yol_bul(self, baslangic_hucre, hedef_hucre):
        """A* algoritması ile yol bulur (engellerden kaçınarak)"""
        # Yol grafiğini oluştur
        graf = {}
        for yol in self.h.yollar:
            for i in range(len(yol) - 1):
                p1_hucre = self._piksel_den_hucresine(yol[i][0], yol[i][1])
                p2_hucre = self._piksel_den_hucresine(yol[i+1][0], yol[i+1][1])
                
                if p1_hucre not in graf:
                    graf[p1_hucre] = []
                if p2_hucre not in graf:
                    graf[p2_hucre] = []
                
                if p2_hucre not in graf[p1_hucre]:
                    graf[p1_hucre].append(p2_hucre)
                if p1_hucre not in graf[p2_hucre]:
                    graf[p2_hucre].append(p1_hucre)
        
        # A* algoritması
        # Priority queue: (f_score, g_score, node, parent)
        open_set = [(0, 0, baslangic_hucre, None)]
        closed_set = set()
        g_scores = {baslangic_hucre: 0}
        came_from = {baslangic_hucre: None}
        
        while open_set:
            # En düşük f_score'a sahip düğümü al
            current_f, current_g, current, parent = heapq.heappop(open_set)
            
            # Eğer bu düğüm zaten kapalıysa atla
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # Hedefe ulaşıldı mı?
            if current == hedef_hucre:
                # Yolu geriye doğru takip et
                yol = []
                node = hedef_hucre
                while node is not None:
                    yol.append(node)
                    node = came_from[node]
                return yol[::-1]  # Ters çevir
            
            # Komşuları değerlendir
            if current in graf:
                for neighbor in graf[current]:
                    if neighbor in closed_set:
                        continue
                    
                    # Komşunun güvenli olup olmadığını kontrol et
                    if not self._hucre_guvenli_mi(neighbor):
                        # Engelli veya yeşil alanda, yüksek maliyet ver (ama tamamen yasaklama)
                        neighbor_cost = 1000  # Çok yüksek maliyet
                    else:
                        # Normal maliyet (mesafe)
                        neighbor_cost = math.hypot(
                            neighbor[0] - current[0],
                            neighbor[1] - current[1]
                        ) * self.h.HUCRE
                    
                    # Tentative g_score
                    tentative_g = g_scores[current] + neighbor_cost
                    
                    # Eğer bu komşu daha önce görülmediyse veya daha iyi bir yol bulduysak
                    if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                        came_from[neighbor] = current
                        g_scores[neighbor] = tentative_g
                        
                        # Heuristik (h_score)
                        h_score = self._heuristic(neighbor, hedef_hucre) * self.h.HUCRE
                        
                        # f_score = g_score + h_score
                        f_score = tentative_g + h_score
                        
                        heapq.heappush(open_set, (f_score, tentative_g, neighbor, current))
        
        return []  # Yol bulunamadı
    
    def _ondaki_araci_tespit_et(self):
        """Öndeki aracı tespit eder ve güvenli mesafe kontrolü yapar"""
        en_yakin_npc = None
        en_yakin_mesafe = float('inf')
        
        # Araç yönü
        radyan = math.radians(self.aci)
        on_vektor_x = math.cos(radyan)
        on_vektor_y = -math.sin(radyan)
        
        for npc in self.get_npcs():
            if npc is self:
                continue
            
            # Öndeki araç kontrolü
            dx = npc.x - self.x
            dy = npc.y - self.y
            
            # Nokta çarpım ile önde olup olmadığını kontrol et
            dot_product = dx * on_vektor_x + dy * on_vektor_y
            if dot_product > 0:  # Önde
                mesafe = math.hypot(dx, dy)
                if mesafe < en_yakin_mesafe:
                    en_yakin_mesafe = mesafe
                    en_yakin_npc = npc
        
        # Ana arabayı kontrol et
        if hasattr(self, 'ana_araba') and self.ana_araba is not None:
            dx = self.ana_araba.x - self.x
            dy = self.ana_araba.y - self.y
            dot_product = dx * on_vektor_x + dy * on_vektor_y
            if dot_product > 0:
                mesafe = math.hypot(dx, dy)
                if mesafe < en_yakin_mesafe:
                    en_yakin_mesafe = mesafe
                    en_yakin_npc = self.ana_araba
        
        return en_yakin_npc, en_yakin_mesafe
    
    def _sensor_temelli_hareket(self):
        """Sensör verilerine göre hareket eder"""
        if len(self.sensor_mesafeleri) < 3:
            return
        
        sol_mesafe = self.sensor_mesafeleri[0]
        on_mesafe = self.sensor_mesafeleri[1]
        sag_mesafe = self.sensor_mesafeleri[2]
        
        # Ana arabayı kontrol et (öncelikli - çarpışma önleme)
        if hasattr(self, 'ana_araba') and self.ana_araba is not None:
            ana_dx = self.ana_araba.x - self.x
            ana_dy = self.ana_araba.y - self.y
            ana_mesafe = math.hypot(ana_dx, ana_dy)
            
            if ana_mesafe < self.ana_araba_guvenli_mesafe:
                # Ana arabaya çok yakın, dur veya yavaşla
                if ana_mesafe < self.ana_araba_guvenli_mesafe * 0.5:
                    # Çok yakın, çok yavaşla ama durma
                    self.hiz = max(self.minimum_hiz * 0.5, self.hiz * 0.5)
                    return
                else:
                    # Yakın, yavaşla ve yön değiştir ama durma
                    self.hiz = max(self.minimum_hiz * 0.7, self.hiz * 0.7)
                    # Ana arabadan uzaklaşmak için yön değiştir
                    ana_aci = math.degrees(math.atan2(-ana_dy, ana_dx))
                    # Ters yöne dön
                    self.aci = ana_aci + 180 + random.uniform(-30, 30)
                    return
        
        # Öndeki aracı kontrol et
        on_arac, arac_mesafe = self._ondaki_araci_tespit_et()
        if on_arac and arac_mesafe < self.guvenli_mesafe:
            # Öndeki araç çok yakın, yavaşla veya dur
            self.hiz = max(0, self.hiz * 0.8 - 0.1)
            return
        
        # Engelleri kontrol et
        for engel in self.get_engeller():
            from engel import TrafikIsigi, YayaGecidi, YolCalismasi, HizKesici
            
            # Trafik ışığı kontrolü - kırmızıysa çok yavaşla (ama durma)
            if isinstance(engel, TrafikIsigi):
                engel_mesafe = math.hypot(engel.pixel_pos[0] - self.x, engel.pixel_pos[1] - self.y)
                if engel_mesafe < 80 and getattr(engel, 'durum', None) == "kirmizi":
                    # Kırmızı ışık, çok yavaşla ama durma
                    self.hiz = max(self.minimum_hiz * 0.5, self.hiz * 0.6)
                    return
            
            # Yaya geçidi kontrolü - yayalar geçiyorsa çok yavaşla (ama durma)
            elif isinstance(engel, YayaGecidi):
                # Yaya geçidine yakınlık kontrolü
                t, dik, uzunluk = engel._proj_ve_mesafe(self.x, self.y)
                if 0 <= t <= uzunluk and dik <= engel.genislik / 2 + 50:  # Yaya geçidine yakınsa
                    if engel.yayalar_aktif_mi and len(engel.yaya_konumlari) > 0:
                        # Yayalar geçiyor, çok yavaşla ama durma
                        self.hiz = max(self.minimum_hiz * 0.6, self.hiz * 0.7)
                        return
                    # Yayalar yoksa normal devam et
            
            # Kasis kontrolü - üzerinden geçerken yavaşla (ama durma)
            elif isinstance(engel, HizKesici):
                if engel.icinde_mi(self.x, self.y):
                    # Kasis üzerindeyiz, hızı azalt ama durma
                    self.hiz = max(self.minimum_hiz, self.hiz * engel.carpma_orani)
                    return
        
        # Engel tespiti - ama hiç durmadan (minimum hız korunmalı)
        if on_mesafe < 50:  # Önde yakın engel var
            if sol_mesafe > sag_mesafe and sol_mesafe > 60:
                # Sola dön (ama sağ taraftan gitmeye çalış)
                self.aci += 1.5
                # Yavaşla ama durma
                self.hiz = max(self.minimum_hiz, self.hiz * 0.85)
            elif sag_mesafe > sol_mesafe and sag_mesafe > 60:
                # Sağa dön
                self.aci -= 1.5
                # Yavaşla ama durma
                self.hiz = max(self.minimum_hiz, self.hiz * 0.85)
            else:
                # Çok yakın engel, yavaşla ama durma
                self.hiz = max(self.minimum_hiz, self.hiz * 0.8)
        elif on_mesafe < 100:  # Önde orta mesafe engel
            self.hiz = max(self.minimum_hiz, self.hiz * 0.95)  # Yavaşla ama durma
        else:
            # Normal hız (maksimum hıza çık)
            self.hiz = min(self.hiz + 0.08, self.maks_hiz)
    
    def _yoldan_cikti_mi(self):
        """Araç yolun dışına çıktı mı kontrol eder"""
        ekran = self.h.ekran
        kontrol_noktasi = (int(self.x), int(self.y))
        if not (0 <= kontrol_noktasi[0] < self.h.GENISLIK and 0 <= kontrol_noktasi[1] < self.h.YUKSEKLIK):
            return True
        
        try:
            renk = ekran.get_at(kontrol_noktasi)
            return self._renk_cimen_mi(renk)
        except:
            return True
    
    def guncelle(self):
        # Sensörleri oku
        self.sensorleri_oku()
        
        # Kasis kontrolü - üzerindeyse yavaşla
        for engel in self.get_engeller():
            from engel import HizKesici
            if isinstance(engel, HizKesici):
                if engel.icinde_mi(self.x, self.y):
                    # Kasis üzerindeyiz, hızı azalt
                    self.hiz = max(0.3, self.hiz * engel.carpma_orani)
        
        # Sensör temelli hareket
        self._sensor_temelli_hareket()
        
        # Otonom mod: A* ile yol bul (sonsuz hareket - hiç durmadan)
        if self.otonom_mod:
            self.son_rota_guncelleme += 1
            self.rastgele_hedef_sayaci += 1
            
            # Rota yoksa veya güncelleme zamanı geldiyse veya hedefe ulaşıldıysa yeni rota bul
            rota_gecersiz = (
                not self.hedef_rota or 
                self.son_rota_guncelleme >= self.rota_guncelleme_araligi or
                self.aktif_hedef_index >= len(self.hedef_rota)
            )
            
            if rota_gecersiz:
                mevcut_hucre = self._piksel_den_hucresine(self.x, self.y)
                
                # Yeni rastgele hedef seç
                yeni_hedef = self._rastgele_hedef_sec()
                if yeni_hedef:
                    hedef_hucre = self._piksel_den_hucresine(yeni_hedef[0], yeni_hedef[1])
                else:
                    # Fallback: Mevcut yolun bitiş noktası
                    hedef_hucre = self._piksel_den_hucresine(self.yol_bitis[0], self.yol_bitis[1])
                
                # A* ile yol bul (engellerden kaçınarak)
                self.hedef_rota = self._astar_yol_bul(mevcut_hucre, hedef_hucre)
                
                # Eğer rota bulunamadıysa, alternatif hedef dene
                if not self.hedef_rota:
                    # Daha yakın bir hedef dene
                    alternatif_hedefler = []
                    for yol in self.h.yollar:
                        if len(yol) >= 2:
                            alternatif_hedefler.append(self._piksel_den_hucresine(yol[0][0], yol[0][1]))
                            alternatif_hedefler.append(self._piksel_den_hucresine(yol[-1][0], yol[-1][1]))
                    
                    for alt_hedef in alternatif_hedefler[:10]:  # İlk 10 alternatif hedefi dene
                        self.hedef_rota = self._astar_yol_bul(mevcut_hucre, alt_hedef)
                        if self.hedef_rota:
                            break
                
                self.aktif_hedef_index = 0
                self.son_rota_guncelleme = 0
            
            # Rota varsa takip et
            if self.hedef_rota and self.aktif_hedef_index < len(self.hedef_rota):
                hedef_hucre = self.hedef_rota[self.aktif_hedef_index]
                hedef_x, hedef_y = self._hucresinden_piksele(hedef_hucre[0], hedef_hucre[1])
                
                # Sağ şerit takibi için yol segmentini bul ve sağ şeritte pozisyon hesapla
                if self.aktif_hedef_index < len(self.hedef_rota) - 1:
                    sonraki_hucre = self.hedef_rota[self.aktif_hedef_index + 1]
                    sonraki_x, sonraki_y = self._hucresinden_piksele(sonraki_hucre[0], sonraki_hucre[1])
                    
                    # Yol segmentini bul ve sağ şeritte pozisyon hesapla
                    segment = self._en_yakin_yol_segmentini_bul(hedef_x, hedef_y)
                    if segment is None:
                        # Segment bulunamadı, basit offset kullan
                        sag_taraf_pozisyon = self._yolun_sag_tarafina_offset_ekle(
                            (hedef_x, hedef_y), (sonraki_x, sonraki_y), self.sag_taraf_offset
                        )
                        hedef_x, hedef_y = sag_taraf_pozisyon
                    else:
                        # Yol segmenti bulundu, sağ şeritte pozisyon hesapla
                        p1, p2, ux, uy, t, seg_uzunluk = segment
                        yol_merkez_x = p1[0] + ux * t
                        yol_merkez_y = p1[1] + uy * t
                        
                        # Sağ taraf vektörü
                        sag_ux = uy
                        sag_uy = -ux
                        
                        # Sağ şeritte hedef pozisyon
                        hedef_x = yol_merkez_x + sag_ux * self.serit_offset_hedef
                        hedef_y = yol_merkez_y + sag_uy * self.serit_offset_hedef
                else:
                    # Son hedef, sağ şeritte pozisyon hesapla
                    segment = self._en_yakin_yol_segmentini_bul(hedef_x, hedef_y)
                    if segment:
                        p1, p2, ux, uy, t, seg_uzunluk = segment
                        yol_merkez_x = p1[0] + ux * t
                        yol_merkez_y = p1[1] + uy * t
                        sag_ux = uy
                        sag_uy = -ux
                        hedef_x = yol_merkez_x + sag_ux * self.serit_offset_hedef
                        hedef_y = yol_merkez_y + sag_uy * self.serit_offset_hedef
                
                mesafe = math.hypot(hedef_x - self.x, hedef_y - self.y)
                if mesafe < self.hedef_toleransi * 1.5:
                    self.aktif_hedef_index += 1
                else:
                    # Hedefe doğru açıyı ayarla
                    dx = hedef_x - self.x
                    dy = hedef_y - self.y
                    hedef_aci = -math.degrees(math.atan2(dy, dx))
                    # Açıyı yumuşak geçişle ayarla
                    aci_fark = hedef_aci - self.aci
                    while aci_fark > 180:
                        aci_fark -= 360
                    while aci_fark < -180:
                        aci_fark += 360
                    self.aci += aci_fark * 0.15  # Yumuşak dönüş
                    
                    # Şerit takibi - sağ şeritte kal
                    self._sag_seritte_kal()
        
        # Şerit takibi - sürekli sağ şeritte kal
        self._sag_seritte_kal()
        
        # Yoldan çıktıysa yavaşla ama durma (yoldan çıkmasını engelle)
        if self._yoldan_cikti_mi():
            self.hiz = max(self.minimum_hiz * 0.7, self.hiz * 0.85)
        
        # Hareket (hiç durmadan)
        hiz_bonusu = 1.0 + min(0.2, (self.yol_genislik - self.h.YOL_KALINLIK) / self.h.YOL_KALINLIK * 0.5)
        aktuel_hiz = self.hiz * hiz_bonusu
        
        # Minimum hız garantisi (hiç durmadan hareket)
        if aktuel_hiz < self.minimum_hiz and not self._yoldan_cikti_mi():
            aktuel_hiz = self.minimum_hiz
        
        rad = math.radians(self.aci)
        yeni_x = self.x + aktuel_hiz * math.cos(rad)
        yeni_y = self.y - aktuel_hiz * math.sin(rad)
        
        # Şerit kontrolü - yeni pozisyonun da sağ şeritte olduğundan emin ol
        segment_yeni = self._en_yakin_yol_segmentini_bul(yeni_x, yeni_y)
        if segment_yeni:
            p1, p2, ux, uy, t, seg_uzunluk = segment_yeni
            yol_merkez_x = p1[0] + ux * t
            yol_merkez_y = p1[1] + uy * t
            
            sapma_dx = yeni_x - yol_merkez_x
            sapma_dy = yeni_y - yol_merkez_y
            sag_ux = uy
            sag_uy = -ux
            sag_projeksiyon = sapma_dx * sag_ux + sapma_dy * sag_uy
            
            # Şerit sınırları kontrolü (yol merkezinden sağa doğru)
            maksimum_offset = self.h.YOL_KALINLIK / 2 - 15  # Yolun sağ kenarına çok yaklaşmadan
            minimum_offset = self.serit_offset_hedef - self.serit_toleransi
            
            # Şerit dışına çıkmışsa düzelt
            if sag_projeksiyon > maksimum_offset:
                # Çok sağa çıkmış, sola kaydır
                duzeltme = (sag_projeksiyon - maksimum_offset) * 0.3
                yeni_x -= sag_ux * duzeltme
                yeni_y -= sag_uy * duzeltme
            elif sag_projeksiyon < minimum_offset:
                # Çok sola çıkmış, sağa kaydır
                duzeltme = (minimum_offset - sag_projeksiyon) * 0.3
                yeni_x += sag_ux * duzeltme
                yeni_y += sag_uy * duzeltme
        
        # Yoldan çıkmamak için kontrol (yeşil alan/çimen engel olarak algılanır)
        # Ön pozisyon kontrolü - çoklu nokta kontrolü
        kontrol_noktalari = []
        radyan = math.radians(self.aci)
        araba_genislik = self.orijinal_gorsel.get_width()
        araba_yukseklik = self.orijinal_gorsel.get_height()
        
        # Araç önü ve kenarları boyunca kontrol noktaları
        kontrol_mesafesi = araba_genislik / 2 * 0.9
        sapma_x = kontrol_mesafesi * math.cos(radyan)
        sapma_y = -kontrol_mesafesi * math.sin(radyan)
        
        yan_nokta_sayisi = 5
        yan_sapma_max = araba_yukseklik / 2 * 0.8
        
        for i in range(yan_nokta_sayisi):
            yan_oran = -1.0 + (i / (yan_nokta_sayisi - 1)) * 2.0
            yan_sapma = yan_sapma_max * yan_oran
            yan_sapma_x = -yan_sapma * math.sin(radyan)
            yan_sapma_y = -yan_sapma * math.cos(radyan)
            
            kontrol_x = yeni_x + sapma_x + yan_sapma_x
            kontrol_y = yeni_y + sapma_y + yan_sapma_y
            kontrol_noktalari.append((kontrol_x, kontrol_y))
        
        # Ana arabayla çarpışma kontrolü (öncelikli)
        ana_araba_carpisma = False
        if hasattr(self, 'ana_araba') and self.ana_araba is not None:
            # Ana arabayla mesafe kontrolü
            yeni_ana_dx = self.ana_araba.x - yeni_x
            yeni_ana_dy = self.ana_araba.y - yeni_y
            yeni_ana_mesafe = math.hypot(yeni_ana_dx, yeni_ana_dy)
            
            # Araç boyutları
            npc_genislik = self.orijinal_gorsel.get_width()
            npc_yukseklik = self.orijinal_gorsel.get_height()
            ana_genislik = self.ana_araba.orijinal_gorsel.get_width()
            ana_yukseklik = self.ana_araba.orijinal_gorsel.get_height()
            
            # Minimum güvenli mesafe (araç boyutları dahil)
            min_carpisma_mesafesi = (npc_genislik + ana_genislik) / 2 + 20
            min_guvenli_mesafe = (npc_genislik + ana_genislik) / 2 + self.ana_araba_guvenli_mesafe
            
            if yeni_ana_mesafe < min_carpisma_mesafesi:
                # Çarpışma riski var, hareket etme
                ana_araba_carpisma = True
            elif yeni_ana_mesafe < min_guvenli_mesafe:
                # Güvenli mesafe altında, yavaşla ama durma
                self.hiz = max(self.minimum_hiz * 0.7, self.hiz * 0.6)
                # Ana arabadan uzaklaşmak için yön değiştir
                ana_aci = math.degrees(math.atan2(-yeni_ana_dy, yeni_ana_dx))
                self.aci = ana_aci + 180 + random.uniform(-20, 20)
                return
        
        guvenli_mi = True
        try:
            for kontrol_x, kontrol_y in kontrol_noktalari:
                if not (0 <= int(kontrol_x) < self.h.GENISLIK and 0 <= int(kontrol_y) < self.h.YUKSEKLIK):
                    guvenli_mi = False
                    break
                
                # Yeşil alan/çimen kontrolü (engel olarak algılanır)
                kontrol_renk = self.h.ekran.get_at((int(kontrol_x), int(kontrol_y)))
                if self._renk_cimen_mi(kontrol_renk):
                    guvenli_mi = False
                    break
                
                # Engelleri kontrol et (yol çalışması, yaya geçidi vb.)
                for engel in self.get_engeller():
                    from engel import YolCalismasi, YayaGecidi
                    
                    # Yol çalışması - engel olarak algılanır, girmemeli
                    if isinstance(engel, YolCalismasi):
                        if engel.carpisti_mi(kontrol_x, kontrol_y):
                            guvenli_mi = False
                            break
                    
                    # Yaya geçidi - yayalar geçiyorsa engel
                    elif isinstance(engel, YayaGecidi):
                        # Yaya geçidine çok yakınsa ve yayalar geçiyorsa dur
                        t, dik, uzunluk = engel._proj_ve_mesafe(kontrol_x, kontrol_y)
                        if 0 <= t <= uzunluk and dik <= engel.genislik / 2 + 30:
                            if engel.yayalar_aktif_mi and len(engel.yaya_konumlari) > 0:
                                guvenli_mi = False
                                break
                    
                    if not guvenli_mi:
                        break
                
                if not guvenli_mi:
                    break
                
                # Ana arabayla çarpışma kontrolü (her kontrol noktası için)
                if hasattr(self, 'ana_araba') and self.ana_araba is not None:
                    kontrol_ana_dx = self.ana_araba.x - kontrol_x
                    kontrol_ana_dy = self.ana_araba.y - kontrol_y
                    kontrol_ana_mesafe = math.hypot(kontrol_ana_dx, kontrol_ana_dy)
                    
                    npc_genislik = self.orijinal_gorsel.get_width()
                    ana_genislik = self.ana_araba.orijinal_gorsel.get_width()
                    min_carpisma_mesafesi = (npc_genislik + ana_genislik) / 2 + 15
                    
                    if kontrol_ana_mesafe < min_carpisma_mesafesi:
                        guvenli_mi = False
                        break
        except (IndexError, ValueError):
            guvenli_mi = False
        
        # Ana arabayla çarpışma varsa çok yavaşla ama durma
        if ana_araba_carpisma:
            self.hiz = max(self.minimum_hiz * 0.4, self.hiz * 0.5)
            # Ana arabadan uzaklaşmak için yön değiştir
            if hasattr(self, 'ana_araba') and self.ana_araba is not None:
                ana_dx = self.ana_araba.x - self.x
                ana_dy = self.ana_araba.y - self.y
                ana_aci = math.degrees(math.atan2(-ana_dy, ana_dx))
                self.aci = ana_aci + 180 + random.uniform(-30, 30)
            return
        
        if guvenli_mi:
            self.x = yeni_x
            self.y = yeni_y
        else:
            # Güvenli değil, yavaşla ama durma
            self.hiz = max(self.minimum_hiz * 0.8, self.hiz * 0.85)
            # Çimen/yeşil alandan uzaklaşmak için açıyı değiştir
            # Sensör verilerine göre yön belirle
            if len(self.sensor_mesafeleri) >= 3:
                sol_mesafe = self.sensor_mesafeleri[0]
                sag_mesafe = self.sensor_mesafeleri[2]
                if sol_mesafe > sag_mesafe:
                    self.aci += 2.0  # Sola dön
                else:
                    self.aci -= 2.0  # Sağa dön
            else:
                # Varsayılan: sağa dön
                self.aci -= 2.0
        
        self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def _aciyi_guncelle(self):
        if self.ileri_yon:
            hedef_x, hedef_y = self.yol_bitis
        else:
            hedef_x, hedef_y = self.yol_baslangic
        dx = hedef_x - self.x
        dy = hedef_y - self.y
        hedef_aci = -math.degrees(math.atan2(dy, dx))
        self.aci = hedef_aci

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
    
    def sensorleri_oku(self):
        """Sensör verilerini okur ve kaydeder"""
        ekran = self.h.ekran
        sensor_acilari = [-45, 0, 45]
        max_mesafe = 100
        self.sensor_mesafeleri = []
        
        for aci_deg in sensor_acilari:
            toplam_aci = math.radians(self.aci - aci_deg)
            carpti_mi = False
            uzaklik = 0
            
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
                        from engel import TrafikIsigi, YolCalismasi, YayaGecidi
                        
                        # Yol çalışması - engel olarak algılanır
                        if isinstance(engel, YolCalismasi):
                            if engel.carpisti_mi(x, y):
                                carpti_mi = True
                                break
                        
                        # Yaya geçidi - yayalar geçiyorsa engel
                        elif isinstance(engel, YayaGecidi):
                            # Yaya geçidine yakınlık kontrolü
                            t, dik, uzunluk = engel._proj_ve_mesafe(x, y)
                            if 0 <= t <= uzunluk and dik <= engel.genislik / 2 + 20:
                                # Yayalar geçiyorsa engel
                                if engel.yayalar_aktif_mi and len(engel.yaya_konumlari) > 0:
                                    carpti_mi = True
                                    break
                        
                        # Trafik ışığı - kırmızıysa engel
                        elif isinstance(engel, TrafikIsigi):
                            if engel.carpisti_mi(x, y) and getattr(engel, 'durum', None) == "kirmizi":
                                carpti_mi = True
                                break
                        
                        # Diğer engeller (genel kontrol)
                        elif engel.carpisti_mi(x, y):
                            carpti_mi = True
                            break
                    if not carpti_mi:
                        # Diğer NPC'leri kontrol et (kendini hariç tut)
                        for npc in self.get_npcs():
                            if npc is self:
                                continue
                            npc_mesafe = math.hypot(npc.x - x, npc.y - y)
                            algilama_mesafe = (self.orijinal_gorsel.get_width() + npc.orijinal_gorsel.get_width()) / 2 + 15
                            if npc_mesafe < algilama_mesafe:
                                carpti_mi = True
                                break
                        # Ana arabayı kontrol et (eğer referans varsa)
                        if hasattr(self, 'ana_araba') and self.ana_araba is not None:
                            ana_araba_mesafe = math.hypot(self.ana_araba.x - x, self.ana_araba.y - y)
                            algilama_mesafe_ana = (self.orijinal_gorsel.get_width() + self.ana_araba.orijinal_gorsel.get_width()) / 2 + 15
                            if ana_araba_mesafe < algilama_mesafe_ana:
                                carpti_mi = True
                if carpti_mi:
                    break
            
            self.sensor_mesafeleri.append(uzaklik)
    
    def sensorleri_ciz(self):
        """NPC arabaların sensörlerini silik (semi-transparent) olarak çizer"""
        ekran = self.h.ekran
        sensor_acilari = [-45, 0, 45]
        max_mesafe = 250
        alpha_değeri = 100  # Silik görünüm için alpha değeri (0-255 arası, 100 = yarı saydam)
        
        for idx, aci_deg in enumerate(sensor_acilari):
            # Sensör mesafesini kayıtlı veriden al
            uzaklik = self.sensor_mesafeleri[idx] if idx < len(self.sensor_mesafeleri) else max_mesafe
            toplam_aci = math.radians(self.aci - aci_deg)
            
            # Renk mesafeye göre belirle
            renk_cizgi_base = (0, 255, 0)  # Yeşil (güvenli)
            if uzaklik < 40:
                renk_cizgi_base = (255, 0, 0)  # Kırmızı (yakın engel)
            elif uzaklik < 80:
                renk_cizgi_base = (255, 255, 0)  # Sarı (orta mesafe)
            
            # Silik renk oluştur (alpha değeri ile)
            renk_cizgi_silik = tuple(min(255, int(c * (alpha_değeri / 255))) for c in renk_cizgi_base[:3])
            
            x_bitis = int(self.x + math.cos(toplam_aci) * uzaklik)
            y_bitis = int(self.y - math.sin(toplam_aci) * uzaklik)
            
            # Silik çizgi çiz (daha ince ve yarı saydam)
            pygame.draw.line(ekran, renk_cizgi_silik, (self.x, self.y), (x_bitis, y_bitis), 1)
            # Silik daire çiz
            pygame.draw.circle(ekran, renk_cizgi_silik, (x_bitis, y_bitis), 3)

    def ciz(self):
        self.h.ekran.blit(self.image, self.rect)
        # Sensörleri çiz
        self.sensorleri_ciz()


def _renk_cimen_mi_static(harita, renk):
    """Statik fonksiyon olarak çimen rengi kontrolü"""
    if len(renk) < 3:
        return False
    c_r, c_g, c_b = harita.CIMEN[:3]
    r_r, r_g, r_b = renk[0], renk[1], renk[2]
    return (c_r == r_r and c_g == r_g and c_b == r_b)

def _pozisyon_yolda_mi(harita, x, y):
    """Pozisyonun yol üzerinde olup olmadığını kontrol eder (yeşil alanda değil)"""
    if not (0 <= int(x) < harita.GENISLIK and 0 <= int(y) < harita.YUKSEKLIK):
        return False
    try:
        renk = harita.ekran.get_at((int(x), int(y)))
        return not _renk_cimen_mi_static(harita, renk)
    except (IndexError, ValueError):
        return False

def npc_arac_uret(harita, araba_uzunluk, araba_genislik, ana_x, ana_y, engeller_ref=None, npc_ref=None):
    duz_yollar = []
    for yol_seg in harita.yollar:
        if len(yol_seg) == 2:
            p1, p2 = yol_seg[0], yol_seg[1]
            mesafe = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if mesafe > harita.HUCRE * 1.5:
                duz_yollar.append(yol_seg)
    if not duz_yollar:
        duz_yollar = [y for y in harita.yollar if len(y) == 2]
    
    guvenli_yollar = []
    minimum_mesafe = harita.HUCRE * 3
    for yol in duz_yollar:
        baslangic_mesafe = math.hypot(yol[0][0] - ana_x, yol[0][1] - ana_y)
        bitis_mesafe = math.hypot(yol[-1][0] - ana_x, yol[-1][1] - ana_y)
        if baslangic_mesafe >= minimum_mesafe and bitis_mesafe >= minimum_mesafe:
            guvenli_yollar.append(yol)
    if not guvenli_yollar:
        minimum_mesafe = harita.HUCRE * 2
        for yol in duz_yollar:
            baslangic_mesafe = math.hypot(yol[0][0] - ana_x, yol[0][1] - ana_y)
            bitis_mesafe = math.hypot(yol[-1][0] - ana_x, yol[-1][1] - ana_y)
            if baslangic_mesafe >= minimum_mesafe and bitis_mesafe >= minimum_mesafe:
                guvenli_yollar.append(yol)
    if not guvenli_yollar:
        guvenli_yollar = duz_yollar
    
    # Her araç için farklı yol seç (üst üste doğmamak için)
    npc_sayisi = min(4, 5)
    kullanilan_yollar = []
    kullanilan_posisyonlar = []  # Kullanılan pozisyonları takip et
    minimum_arac_mesafesi = max(araba_uzunluk, araba_genislik) * 2.5  # Araçlar arası minimum mesafe
    
    # Mevcut yolları karıştır
    random.shuffle(guvenli_yollar)
    
    for i in range(npc_sayisi):
        uygun_yol_bulundu = False
        
        # Her yol için deneme yap
        for yol in guvenli_yollar:
            if yol in kullanilan_yollar:
                continue  # Bu yol zaten kullanıldı
            
            yol_baslangic = yol[0]
            yol_bitis = yol[-1]
            
            # Yol üzerinde rastgele bir pozisyon seç (başlangıçtan bitişe)
            yol_uzunlugu = math.hypot(yol_bitis[0] - yol_baslangic[0], yol_bitis[1] - yol_baslangic[1])
            if yol_uzunlugu < araba_uzunluk * 2:
                continue  # Yol çok kısa
            
            # Yol üzerinde birkaç farklı pozisyon dene
            for deneme in range(5):
                # 0.2 ile 0.8 arası yol üzerinde rastgele pozisyon
                yol_orani = random.uniform(0.2, 0.8)
                baslangic_x = yol_baslangic[0] + (yol_bitis[0] - yol_baslangic[0]) * yol_orani
                baslangic_y = yol_baslangic[1] + (yol_bitis[1] - yol_baslangic[1]) * yol_orani
                
                # Yeşil alanda doğmamalı kontrolü
                if not _pozisyon_yolda_mi(harita, baslangic_x, baslangic_y):
                    continue  # Yeşil alanda, başka pozisyon dene
                
                # Diğer NPC'lerden yeterince uzak mı kontrol et
                yeterince_uzak = True
                for kullanilan_pos in kullanilan_posisyonlar:
                    mesafe = math.hypot(kullanilan_pos[0] - baslangic_x, kullanilan_pos[1] - baslangic_y)
                    if mesafe < minimum_arac_mesafesi:
                        yeterince_uzak = False
                        break
                
                if yeterince_uzak:
                    # Ana arabadan da uzak olmalı
                    ana_mesafe = math.hypot(ana_x - baslangic_x, ana_y - baslangic_y)
                    if ana_mesafe >= minimum_mesafe:
                        # Uygun pozisyon bulundu
                        kullanilan_yollar.append(yol)
                        kullanilan_posisyonlar.append((baslangic_x, baslangic_y))
                        uygun_yol_bulundu = True
                        break
            
            if uygun_yol_bulundu:
                break
        
        # Uygun yol bulunamadıysa, yine de bir yol seç (son çare)
        if not uygun_yol_bulundu and guvenli_yollar:
            # En az kullanılan yolu veya rastgele bir yolu seç
            kullanilmayan_yollar = [y for y in guvenli_yollar if y not in kullanilan_yollar]
            if kullanilmayan_yollar:
                yol = random.choice(kullanilmayan_yollar)
            else:
                yol = random.choice(guvenli_yollar)
            
            yol_baslangic = yol[0]
            yol_bitis = yol[-1]
            # Basitçe başlangıç noktasını kullan
            baslangic_x = yol_baslangic[0]
            baslangic_y = yol_baslangic[1]
            
            # Eğer yeşil alandaysa, yol ortasına al
            if not _pozisyon_yolda_mi(harita, baslangic_x, baslangic_y):
                baslangic_x = (yol_baslangic[0] + yol_bitis[0]) / 2
                baslangic_y = (yol_baslangic[1] + yol_bitis[1]) / 2
            
            kullanilan_yollar.append(yol)
            kullanilan_posisyonlar.append((baslangic_x, baslangic_y))
            uygun_yol_bulundu = True
        
        if not uygun_yol_bulundu:
            continue  # Bu NPC oluşturulamadı, atla
    
    # NPC'leri oluştur
    npcs = []
    for i, (yol, pozisyon) in enumerate(zip(kullanilan_yollar[:npc_sayisi], kullanilan_posisyonlar[:npc_sayisi])):
        baslangic_x, baslangic_y = pozisyon
        yol_baslangic = yol[0]
        yol_bitis = yol[-1]
        renk = [random.randint(0, 255) for _ in range(3)]
        resim_yolu = f"araba{i+1}.png"
        npc = NPCArac(harita, baslangic_x, baslangic_y, araba_uzunluk, araba_genislik, yol_baslangic=yol_baslangic, yol_bitis=yol_bitis, yol_genislik=harita.YOL_KALINLIK, resim_yolu=resim_yolu, yedek_renk=tuple(renk), engeller_ref=engeller_ref, npc_ref=npc_ref)
        npcs.append(npc)
    
    return npcs
