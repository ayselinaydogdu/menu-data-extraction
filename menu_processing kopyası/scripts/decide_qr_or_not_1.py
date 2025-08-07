import cv2
import os

os.environ[
    'DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'  # macOS kullanıcıları için kütüphane yolu ayarı (Gerekliyse aktif edin)
from pyzbar import pyzbar
import requests
from bs4 import BeautifulSoup
import re
import csv  # CSV işlemleri için gerekli kütüphane


# --- Yardımcı Fonksiyonlar ---

def musteri_kodu_al(image_path):
    # Dosya yolundaki parantez içindeki uzun sayıyı yakalar
    for part in reversed(image_path.split(os.sep)):
        match = re.search(r'\((\d{6,})\)', part)
        if match:
            return match.group(1)
    return "Bilinmiyor"


def detect_qr_strict(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"️ Görsel yüklenemedi: {image_path}")
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    detector = cv2.QRCodeDetector()
    retval, bbox = detector.detect(gray)
    barcodes = pyzbar.decode(gray)

    return retval and len(barcodes) > 0


def read_qr_opencv(image_path):  # OpenCV kullanarak bir görseldeki QR kodu oku.
    img = cv2.imread(image_path)
    if img is None:
        print(f" Görsel yüklenemedi (OpenCV): {image_path}")
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(gray)
    return data if data else None


def read_qr_pyzbar(image_path):  # pyzbar kütüphanesini kullanarak bir görseldeki QR kodu oku
    img = cv2.imread(image_path)
    if img is None:
        print(f" Görsel yüklenemedi (pyzbar): {image_path}")
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    barcodes = pyzbar.decode(gray)
    if barcodes:
        return barcodes[0].data.decode("utf-8")
    return None


def read_qr_zxing_api(image_path):  # ZXing adlı çevrimiçi API'yi kullanarak görseldeki QR kodu oku.
    try:
        with open(image_path, "rb") as f:
            files = {
                "f": (os.path.basename(image_path), f, "image/jpeg")
            }
            # ZXing API'sine yapılan istek: (Internet bağlantısı gereklidir)
            response = requests.post("https://zxing.org/w/decode", files=files, timeout=10)  # Timeout eklendi
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                pre = soup.find("pre")
                if pre:
                    return pre.text.strip()
    except requests.exceptions.Timeout:
        print(f" ZXing API zaman aşımı: {os.path.basename(image_path)}")
    except Exception as e:
        print(f" ZXing API hatası: {e}")
    return None


def read_qr_combined(image_path):
    if not detect_qr_strict(image_path):
        return "Görsel QR değil"

    for reader_func in [read_qr_opencv, read_qr_pyzbar, read_qr_zxing_api]:
        result = reader_func(image_path)
        if result:
            print(f"🔹 {reader_func.__name__} ile okundu.")
            return result

    return "QR var ama okunamadı"


# --- Ana Raporlama Fonksiyonu (CSV Çıktısı İçin Güncellendi) ---

# Fonksiyon adını daha açıklayıcı olması için değiştirdim
def process_qr_to_csv(root_folder, output_csv_path="qr_log.csv"):
    # Çıktı klasörünün varlığını kontrol et ve gerekirse oluştur
    output_dir = os.path.dirname(output_csv_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # CSV dosyasını yazma modunda aç
    with open(output_csv_path, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)

        # CSV Başlık Satırı
        # AI agent'ına vereceğin için standart CSV formatı (virgülden sonra boşluksuz) en iyisidir.
        csv_writer.writerow(["Müşteri Kodu", "Dosya Adı", "QR Verisi/Durumu"])

        for mekan_folder_name in os.listdir(root_folder):  # mekan_folder adını mekan_folder_name olarak değiştirdim
            mekan_path = os.path.join(root_folder, mekan_folder_name)
            if not os.path.isdir(mekan_path):
                continue

            menu_folder = os.path.join(mekan_path, "Menü Fotoğrafları")
            if not os.path.exists(menu_folder):
                found = False
                for alt_klasor in os.listdir(mekan_path):
                    alt_path = os.path.join(mekan_path, alt_klasor)
                    if os.path.isdir(alt_path):
                        olasi_menu = os.path.join(alt_path, "Menü Fotoğrafları")
                        if os.path.exists(olasi_menu):
                            menu_folder = olasi_menu
                            found = True
                            break
                if not found:
                    msg = f" Menü Fotoğrafları klasörü bulunamadı: {mekan_path}"
                    print(msg)
                    # CSV'ye de bu durumu yazabiliriz
                    # musteri_kodu_al(mekan_path) çağrısı ile klasörden müşteri kodunu alıyoruz
                    csv_writer.writerow([musteri_kodu_al(mekan_path), mekan_folder_name, msg])
                    continue

            for filename in os.listdir(menu_folder):
                # .png uzantısını da ekledik
                if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    image_path = os.path.join(menu_folder, filename)
                    musteri_kodu = musteri_kodu_al(image_path)
                    qr_data = read_qr_combined(image_path)

                    # CSV'ye satır yaz
                    csv_writer.writerow([musteri_kodu, filename, qr_data])
                    print(f" {musteri_kodu} - {filename} : {qr_data}")


# --- Ana Çalışma Bloğu ---
if __name__ == "__main__":
    # PHOTOS_ROOT değişkenindeki fazla boşlukları temizleyelim (eğer varsa).
    photos_root = "/Users/ayselin/Desktop/deneme_klasörü".strip()  # Kendi yolunuzu buraya yazın

    # Raporlama fonksiyonunu çağırırken CSV dosya yolunu belirt
    # output_csv_path parametresine istediğiniz CSV dosya adını verin
    process_qr_to_csv(photos_root, output_csv_path="qr_links_musteri_kodlari.csv")
    print(" qr_links_musteri_kodlari.csv oluşturuldu.")