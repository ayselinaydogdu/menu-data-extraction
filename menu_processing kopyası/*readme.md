# Menü Veri Çıkarma Projesi

Bu proje, farklı formatlardaki menü verilerinden (görsel, PDF, QR kod linki, web sitesi bağlantısı) ürün adı ve fiyat bilgilerini otomatik olarak çıkartır ve bu bilgileri standart bir Excel (CSV) formatında kayıt altına alır.

## 🧠 Kullanılan Araçlar ve API'ler

- **Claude (Anthropic)**: Menü görsellerinden ve Firecrawl’dan gelen verilerden ürün-fiyat bilgisi çıkartmak için kullanılır.
- **Firecrawl API**: Web sitesi linki içeren QR verilerini analiz etmek için kullanılır.
- **OpenCV, Pyzbar, Zxing**: QR kod tespiti ve analizi için kullanılır.
- **pandas, pdf2image, requests** gibi Python kütüphaneleri.

---

## 🗂️ Klasör Yapısı

## scripts klasörü:
Projedeki tüm Python kod dosyaları bu klasörde yer almakta ve sırasıyla numaralandırılmıştır. İçerisinde bulunan dosyalar şunlardır:
decide_qr_or_not_1.py
image_isNot_qr_2.py
web_linkleri_firecrawl_3.py
merge_csv_convertExcel_4.py
run_all_5.py (Tüm kodlar tek bir script üzerinden çalıştırılabilir: (run_all_5.py) Bu betik sırasıyla aşağıdaki adımları otomatik olarak gerçekleştirir:

### 1. `decide_qr_or_not_1.py`
- `photos/` klasörü altındaki menü görselleri taranır.
- Görsel üzerinde QR kod olup olmadığı analiz edilir.
- QR verisi içeren ya da içermeyen her görsel, `qr_links_musteri_kodlari.csv` dosyasına kaydedilir.

---

### 2. `image_isNot_qr_2.py`
- QR kodu içermeyen görseller, `.pdf` uzantılı linkler veya Google Drive linkleri tespit edilir.
- Her biri Claude API ile analiz edilerek `analysis.csv` dosyasına yazılır.
- Eğer bir bağlantı web sitesi linkiyse, "Firecrawl ile okunacak" notu eklenir.

---

### 3. `web_linkleri_firecrawl_3.py`
- "Firecrawl ile okunacak" olarak işaretlenen web linkleri alınır.
- Web sayfası Firecrawl ile taranır, içerik Claude API ile analiz edilir.
- Sonuçlar `firecrawl_results.csv` dosyasına yazılır.

---

### 4. `merge_csv_convertExce_4.py`
- `analysis.csv` ve `firecrawl_results.csv` birleştirilir.
- Eksik fiyatlar `"n/a"` olarak doldurulur.
- Nihai liste `combined_menu_list.csv` ve `combined_menu_list.xlsx` olarak kaydedilir.


## input_data klasörü:
Menü görsellerinin bulunduğu photos adlı alt klasörü içerir.

## prompt_anthropic klasörü:
Yapay zeka modeli Claude için kullanılan prompt.txt adlı dosyayı barındırır. image_isNot_qr_2.py bu pyhton betiği çalıştırılırken bu prompt modelin prompt gerektiren kısmında kullanılır

## docs klasörü:
İş prosedür dokümanı ve proje sunum dosyalarını içerir.


## 📦 Çıktı Dosyaları

| Dosya Adı                  | Açıklama                                             |
|---------------------------|------------------------------------------------------|
| `qr_links_musteri_kodlari.csv` | QR kod analiz sonuçları                           |
| `analysis.csv`            | Görsel ve PDF analiz sonuçları                      |
| `firecrawl_results.csv`   | Web sitesi linklerinden çıkarılan menü verisi       |
| `combined_menu_list.csv`  | Tüm verilerin birleştirilmiş hali (CSV)             |
| `combined_menu_list.xlsx` | Nihai menü verisi (Excel formatında)                |

---

## 📝 Notlar

- run_all_5.py adlı Python dosyası, tüm işlem sırasını otomatik olarak gerçekleştirmek için kullanılmaktadır.

- Bu işlemin sorunsuz çalışabilmesi için:
Tüm .py uzantılı script dosyaları ve prompt anthropic klasöründeki propmt.txt dosyası içerisinde yer alan propmt içeriği, kod içinde(image_isNot_qr_2.py) ilgili yere entegre edilmelidir. Aynı proje klasörü altında ve uygun bir IDE (örneğin PyCharm, VSCode) üzerinde çalıştırılmaya hazır olmalıdır.

- Bu kurulum ve çalıştırma adımları tamamlandığında, uçtan uca otomasyon başarıyla yürütülür ve proje sonunda standart, düzenli bir Excel çıktısı elde edilir.

## 📧 Sorumlular

- Ayselin Aydoğdu  
- Dilan Üzümcü  
- Mehmet Taşkıranoğlu  
- Yasin Bulut  

---


