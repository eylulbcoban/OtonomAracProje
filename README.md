## Teknik Altyapı ve Mimari

Bu proje Ypay Zekaya Giriş dersi kapsamında gelişririlmiştir. Otonom araç algoritmalarının dinamik bir trafik ortamında nasıl tepki verdiğini test etmek ve görselleştirmek amacıyla geliştirilmiştir. Projenin simülasyon ve görselleştirme katmanında **Python 3** ve **Pygame** kütüphanesi kullanılmıştır.

### Simülasyon ve Çevre Modellemesi
* **Graf Tabanlı Harita:** Yol ağları, şeritler ve kavşaklar birer yönlü çizge (directed graph) olarak modellenmiştir. Düğümler (nodes) ve kenar maliyetleri (edge weights) dinamik yapıda olup, `manuel_dugumler.json` üzerinden yönetilebilir durumdadır.
* **Dinamik Engeller (Obstacles):** Harita üzerinde aracın hızını, yönünü ve rota maliyetini etkileyen, polimorfik yapıda gerçek hayat senaryoları kodlanmıştır:
  * *Trafik Işıkları:* Işığın durumuna (kırmızı/yeşil) göre algoritmaya dinamik bekleme cezası (cost) ekler.
  * *Yaya Geçidi & Yol Çalışması:* İçerisinden geçişin zor veya imkansız olduğu yüksek maliyetli alanlar oluşturarak aracın alternatif rotalar hesaplamasını sağlar.
  * *Hız Kesiciler (Kasisler) & Kaygan Zemin:* Aracın anlık ivmelenmesini, maksimum hızını ve sürüş dinamiklerini fiziksel formüllerle manipüle eder.
* **NPC Araçlar:** Ortamda rastgele hareket eden NPC araçlar, ana otonom aracın statik değil sürekli değişen dinamik bir trafikte rota güncellemesi yapabilmesini test etmek için eklenmiştir.

### Yol Bulma Algoritmalar (Pathfinding)
Aracın bulunduğu başlangıç noktasından (A, B veya C) hedefe giderken anlık en iyi rotayı belirlemesi için 6 farklı arama algoritması entegre edilmiştir. Modüler yapı sayesinde simülasyon çalışırken algoritmalar arası geçiş yapılabilir:

1. **Sezgisel Olmayan Aramalar (Uninformed Search):**
   * **BFS (Breadth-First Search):** Tüm yolları eşit maliyette varsayarak sığdan derine tarama yapar.
   * **DFS (Depth-First Search):** Bir yol ayrımında sonuca ulaşana kadar veya çıkmaza girene kadar derinlemesine ilerler.
   * **UCS (Uniform Cost Search / Dijkstra):** Sadece geçmişten gelen yol ve engel maliyetlerini (G-cost) dikkate alarak kesin optimal rotayı garantiler.

2. **Sezgisel Aramalar (Informed Search):**
   * **Greedy Best-First Search:** Sadece hedefe olan tahmini mesafeyi (Kuş uçuşu / Euclidean heuristiği vb.) dikkate alarak rotayı hızlıca, ancak her zaman optimal olmayacak şekilde çizer.
   * **A* (A-Star):** UCS ve Greedy algoritmalarının avantajlarını birleştirir ($f(n) = g(n) + h(n)$). Dinamik engel cezalarını ve tahmini varış süresini hesaplayarak en optimal ve verimli rotayı bulur.
   * **IDA* (Iterative Deepening A*):** A* algoritmasının mantığını kullanır ancak aramayı maliyet eşikleriyle sınırlandırarak bellek (RAM) kullanımını çok daha verimli hale getirir.

### ⚙️ Maliyet Hesaplama Mekanizması (Cost Function)
Arama algoritmaları sadece iki nokta arasındaki mesafeyi ölçmekle kalmaz; kenar maliyetlerini hesaplarken anlık durumları gözetir:
`Toplam Maliyet = Temel Mesafe Maliyeti + Dinamik Engel Cezası (Işık, Yol Çalışması vb.)`
Bu mimari sayesinde araç; kısa rotada kırmızı ışık veya yol çalışması varsa, algoritmik olarak daha uzun ama zaman/maliyet açısından daha ucuz olan alternatif rotalara yönelebilmektedir.
