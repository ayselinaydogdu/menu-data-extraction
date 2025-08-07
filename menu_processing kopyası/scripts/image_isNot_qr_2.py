from io import BytesIO
import os
import re
import base64
import csv
import requests
import pandas as pd
from pdf2image import convert_from_path
from anthropic import Anthropic
import cv2

INPUT_CSV_PATH = "qr_links_musteri_kodlari.csv"
PHOTOS_ROOT = "/Users/ayselin/Desktop/deneme_klasörü"
ANTHROPIC_API_KEY = "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"
DRIVE_API_KEY = "AIzaSyB5L-Dji4FJ1Aa8l5S1lqoylsNx7PowjfU"
MENU_LIST_CSV_PATH = "analysis.csv"

def musteri_kodu_al_from_path(path):
    for part in reversed(path.split(os.sep)):
        match = re.search(r'\((\d{6,})\)', part)
        if match:
            return match.group(1)
    return "Bilinmiyor"


def load_prompt_text(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def find_specific_menu_image(customer_code, target_filename, root_folder=PHOTOS_ROOT):
    for entry in os.listdir(root_folder):
        if customer_code in entry:
            customer_folder_path = os.path.join(root_folder, entry)
            if os.path.isdir(customer_folder_path):
                menu_folder = os.path.join(customer_folder_path, "Menü Fotoğrafları")
                if os.path.isdir(menu_folder):
                    dosyalar = os.listdir(menu_folder)
                    dosyalar_lower = [f.lower() for f in dosyalar]
                    target_filename_lower = target_filename.lower()
                    if target_filename_lower in dosyalar_lower:
                        gerçek_dosya_adı = dosyalar[dosyalar_lower.index(target_filename_lower)]
                        tam_yol = os.path.join(menu_folder, gerçek_dosya_adı)
                        print(f"[DEBUG] Görsel bulundu: {tam_yol}")
                        return tam_yol
                    else:
                        print(f"[DEBUG] Menü klasöründe '{target_filename}' adlı dosya bulunamadı.")
                else:
                    print(f"[DEBUG] Menü Fotoğrafları klasörü bulunamadı: {menu_folder}")
    print(f"[DEBUG] '{customer_code}' için görsel bulunamadı.")
    return None

def enhance_contrast_hist_eq(gray_image):
    print(" Görselin kontrastı artırıldı (histogram eşitleme)")
    return cv2.equalizeHist(gray_image)

def encode_image_to_base64(image_path, to_grayscale=True, enhance_contrast=False):
    try:
        print(f"[INFO] Base64'e çevirme işlemi başladı: {image_path}")

        # Görseli OpenCV ile oku
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] Görsel okunamadı: {image_path}")
            return None, None

        # Grayscale ve kontrast artırma
        if to_grayscale:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            print(" Görsel grayscale formatına çevrildi")

            # Kontrast artır (Histogram Eşitleme)
            image = enhance_contrast_hist_eq(image)

        # Encode et (JPG formatında)
        success, encoded_image = cv2.imencode('.jpg', image)
        if not success:
            print(f"[ERROR] Görsel encode edilemedi: {image_path}")
            return None, None

        # Base64'e çevir
        b64_encoded = base64.b64encode(encoded_image).decode("utf-8")
        media_type = "image/jpeg"
        return b64_encoded, media_type

    except Exception as e:
        print(f"[ERROR] Görsel Base64'e dönüştürülemedi: {image_path}. Hata: {e}")
        return None, None


def query_anthropic_vision(base64_image, media_type, text, client):
    if not base64_image or not media_type:
        return "Görsel işlenemedi (Base64 dönüştürme hatası veya medya tipi yok)."

    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4096,       # menüdeki ürün fazlalığına göre buradaki değer arttırılabilir, eksik ürün listelememek adına
            temperature=0.3,
            system="You are an assistant that extracts information from menu images. Extract product names and prices when the text is readable, even if the image has slight angles or imperfections.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": anthropic_prompt
                        }
                    ]
                }
            ]
        )
        print("[INFO] Claude API yanıtı alındı. İşlem tamamlandı.")
        return response.content[0].text
    except Exception as e:
        error_message = str(e)
        if "credit balance is too low" in error_message.lower():
            return "API kredisi yetersiz: Lütfen kredi yükleyin veya bekleyin."
        return f"Anthropic API hatası: {error_message}"

def download_pdf_from_url(pdf_url, customer_code):
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)
    filename = f"{customer_code}.pdf"
    pdf_path = os.path.join(download_dir, filename)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": pdf_url,
        "Accept-Language": "tr-TR,tr;q=0.9"
    }
    try:
        response = requests.get(pdf_url, headers=headers)
        response.raise_for_status()
        if "application/pdf" in response.headers.get("Content-Type", ""):
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            print(f" PDF indirildi: {pdf_path}")
            return pdf_path
        else:
            print(f" PDF indirilemedi (Content-Type uygun değil): {pdf_url}")
            return None
    except Exception as e:
        print(f" PDF indirilemedi: {pdf_url}. Hata: {e}")
        return None

def extract_folder_id(drive_url):
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", drive_url)
    if match:
        return match.group(1)
    match = re.search(r"id=([a-zA-Z0-9_-]+)", drive_url)
    if match:
        return match.group(1)
    return None

def append_to_menu_list(musteri_kodu, urun_adi, fiyat, not_):
    with open(MENU_LIST_CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([urun_adi, fiyat, musteri_kodu, not_])

def drive_case(anthropic_prompt, qr_drive_linkli_kayitlar, client):
    for index, row in qr_drive_linkli_kayitlar.iterrows():
        drive_url = str(row['QR Verisi/Durumu']).strip()
        customer_code = str(row['Müşteri Kodu']).strip()

        print(f"\n--- Google Drive klasörü işleniyor: Müşteri Kodu: {customer_code}, Link: {drive_url} ---")

        folder_id = extract_folder_id(drive_url)
        if not folder_id:
            print(" Drive linkinden klasör ID alınamadı.")
            append_to_menu_list(customer_code, "", "", "Drive linkinden klasör ID alınamadı")
            continue

        list_url = f'https://www.googleapis.com/drive/v3/files?q="{folder_id}"+in+parents&key={DRIVE_API_KEY}&fields=files(id,name,mimeType)'
        response = requests.get(list_url)

        if response.status_code != 200:
            print(f" Dosya listeleme başarısız: {response.text}")
            append_to_menu_list(customer_code, "", "", "Drive API dosya listeleme hatası")
            continue

        files = response.json().get('files', [])
        if not files:
            print("️Klasörde dosya bulunamadı.")
            append_to_menu_list(customer_code, "", "", "Drive klasöründe dosya yok")
            continue

        print(f" {len(files)} dosya bulundu.")

        for file in files:
            if file['mimeType'] != 'application/pdf':
                continue

            file_id = file['id']
            file_name = file['name']
            download_url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={DRIVE_API_KEY}'
            local_pdf_path = os.path.join("downloads", f"{customer_code}_{file_name}")
            os.makedirs("downloads", exist_ok=True)

            try:
                r = requests.get(download_url)
                r.raise_for_status()
                with open(local_pdf_path, 'wb') as f:
                    f.write(r.content)
                print(f" PDF indirildi: {local_pdf_path}")
            except Exception as e:
                print(f" PDF indirilemedi: {file_name}. Hata: {e}")
                append_to_menu_list(customer_code, "", "", f"Drive PDF indirme hatası: {e}")
                continue

            try:
                images = convert_from_path(local_pdf_path)
                print(f"   {len(images)} sayfa bulundu ve görsellere çevrildi.")

                for page_num, image in enumerate(images, start=1):
                    buffer = BytesIO()
                    image.save(buffer, format="JPEG")
                    buffer.seek(0)
                    image_bytes = buffer.read()
                    base64_encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                    media_type = "image/jpeg"

                    print(f"   {customer_code}_page{page_num}.jpg oluşturuldu.")

                    if base64_encoded_image and media_type:
                        anthropic_response = query_anthropic_vision(base64_encoded_image, media_type, anthropic_prompt, client)
                        print(f"   Sayfa {page_num} analizi: {anthropic_response}")

                        if "API kredisi yetersiz" in anthropic_response or anthropic_response.startswith("Anthropic API hatası"):
                            append_to_menu_list(customer_code, "", "", anthropic_response)
                        else:
                            for line in anthropic_response.strip().split("\n"):
                                line = line.strip()
                                if not line:
                                    continue
                                parts = line.rsplit("-", 1)  # sondan 1 kez ayır
                                if len(parts) == 2:
                                    urun_adi_raw = parts[0].strip()
                                    fiyat = parts[1].strip()
                                    urun_adi = " ".join([p.strip() for p in
                                                         urun_adi_raw.split(
                                                             "-")])  # ürün adındaki '-' işaretlerini boşluk yap
                                    append_to_menu_list(customer_code, urun_adi, fiyat, "")

                                else:

                                    # Eğer line anlamlı bir hata veya uyarı mesajıysa, ürün adı boş, not sütununa yaz
                                    append_to_menu_list(customer_code, "", "", line)
                    else:
                        print(f"   Sayfa {page_num} dönüştürülemedi.")
                        append_to_menu_list(customer_code, "", "", "Görsel dönüştürme/medya tipi hatası")
            except Exception as e:
                print(f"   PDF işlenirken hata oluştu: {e}")
                append_to_menu_list(customer_code, "", "", f"PDF işleme hatası: {e}")

if __name__ == "__main__":
    PHOTOS_ROOT = PHOTOS_ROOT.strip()

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "YOUR_ANTHROPIC_API_KEY_HERE":
        print("Hata: ANTHROPIC_API_KEY ayarlanmamış veya varsayılan değerde.")
        exit()
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        anthropic_prompt = load_prompt_text("prompt_anthropic.txt")
        if not anthropic_prompt.strip():
            raise ValueError("Prompt metni boş.")
    except Exception as e:
        print(f"Hata: prompt dosyası okunamadı: {e}")
        exit()

    try:
        df = pd.read_csv(INPUT_CSV_PATH)
        df.columns = df.columns.str.strip()
    except FileNotFoundError:
        print(f"Hata: Giriş CSV dosyası bulunamadı: {INPUT_CSV_PATH}.")
        exit()
    except Exception as e:
        print(f"Giriş CSV dosyası okunurken hata oluştu: {e}")
        exit()

    qr_degil_kayitlar = df[df['QR Verisi/Durumu'].str.strip() == 'Görsel QR değil']
    qr_pdf_linkli_kayitlar = df[df['QR Verisi/Durumu'].str.strip().str.lower().str.endswith('.pdf')]
    qr_drive_linkli_kayitlar = df[df['QR Verisi/Durumu'].str.strip().str.lower().str.startswith("https://drive.google.com")]

    qr_web_linkli_kayitlar = df[
        (df['QR Verisi/Durumu'].str.strip().str.lower().str.startswith("http")) &
        (~df['QR Verisi/Durumu'].str.strip().str.lower().str.endswith(".pdf")) &
        (~df['QR Verisi/Durumu'].str.strip().str.lower().str.startswith("https://drive.google.com"))
    ]

    if qr_degil_kayitlar.empty and qr_pdf_linkli_kayitlar.empty and qr_web_linkli_kayitlar.empty:
        print(f"'{INPUT_CSV_PATH}' dosyasında işlenecek 'Görsel QR değil', .pdf ya da web sitesi kaydı bulunamadı. İşlem sonlandırıldı.")
        exit()

    # Menü listesi CSV dosyasını başlat, başlıkları yaz
    with open(MENU_LIST_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer_menu = csv.writer(f)
        writer_menu.writerow(["Product Name", "Price", "Customer Code", "Note"])

    # Görsel QR değil kayıtları işle
    for index, row in qr_degil_kayitlar.iterrows():
        customer_code = str(row['Müşteri Kodu']).strip()
        filename = str(row['Dosya Adı']).strip()

        print(f"\n--- Görsel İşleniyor: Müşteri Kodu: {customer_code}, Dosya Adı: {filename} ---")
        image_full_path = find_specific_menu_image(customer_code, filename, PHOTOS_ROOT)

        if image_full_path and os.path.exists(image_full_path):
            print(f"   Görsel bulundu: {image_full_path}")
            base64_encoded_image, media_type = encode_image_to_base64(image_full_path)

            if base64_encoded_image and media_type:
                anthropic_response = query_anthropic_vision(base64_encoded_image, media_type, anthropic_prompt, client)
                print(f"  🤖 Anthropic Analizi: {anthropic_response}")

                if "API kredisi yetersiz" in anthropic_response or anthropic_response.startswith("Anthropic API hatası"):
                    append_to_menu_list(customer_code, "", "", anthropic_response)
                else:
                    for line in anthropic_response.strip().split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.rsplit("-", 1)  # sondan 1 kez ayır
                        if len(parts) == 2:
                            urun_adi_raw = parts[0].strip()
                            fiyat = parts[1].strip()
                            urun_adi = " ".join([p.strip() for p in
                                                 urun_adi_raw.split("-")])  # ürün adındaki '-' işaretlerini boşluk yap
                            append_to_menu_list(customer_code, urun_adi, fiyat, "")

                        else:
                            # Eğer line anlamlı bir hata veya uyarı mesajıysa, ürün adı boş, not sütununa yaz
                            append_to_menu_list(customer_code, "", "", line)
            else:
                print(f"   Görsel Base64'e dönüştürülemedi veya medya tipi belirlenemedi.")
                append_to_menu_list(customer_code, "", "", "Görsel dönüştürme/medya tipi hatası")
        else:
            print(f"   Görsel bulunamadı veya erişilemedi: {filename} için Müşteri Kodu {customer_code}.")
            append_to_menu_list(customer_code, "", "", "Görsel yolu bulunamadı/geçersiz")

    # PDF bağlantılı kayıtları işle
    for index, row in qr_pdf_linkli_kayitlar.iterrows():
        customer_code = str(row['Müşteri Kodu']).strip()
        pdf_path = str(row['QR Verisi/Durumu']).strip()

        print(f"\n--- PDF İşleniyor: Müşteri Kodu: {customer_code}, PDF: {pdf_path} ---")

        if pdf_path.lower().startswith("http://") or pdf_path.lower().startswith("https://"):
            print(f"   PDF URL olarak algılandı, indiriliyor...")
            local_pdf_path = download_pdf_from_url(pdf_path, customer_code)
            if not local_pdf_path:
                print(f"   PDF indirilemedi, işleme devam edilemiyor.")
                append_to_menu_list(customer_code, "", "", "PDF indirilemedi")
                continue
        else:
            local_pdf_path = pdf_path

        if not os.path.exists(local_pdf_path):
            print(f"  ️ PDF yolu bulunamadı veya erişilemedi: {local_pdf_path}")
            append_to_menu_list(customer_code, "", "", "PDF yolu bulunamadı")
            continue

        try:
            images = convert_from_path(local_pdf_path)
            print(f"   {len(images)} sayfa bulundu ve görsellere çevrildi.")

            for page_num, image in enumerate(images, start=1):
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                buffer.seek(0)
                image_bytes = buffer.read()
                base64_encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                media_type = "image/jpeg"

                print(f"   {customer_code}_page{page_num}.jpg oluşturuldu.")

                if base64_encoded_image and media_type:
                    anthropic_response = query_anthropic_vision(base64_encoded_image, media_type, anthropic_prompt, client)
                    print(f"   Sayfa {page_num} analizi: {anthropic_response}")

                    if "API kredisi yetersiz" in anthropic_response or anthropic_response.startswith("Anthropic API hatası"):
                        append_to_menu_list(customer_code, "", "", anthropic_response)
                    else:
                        for line in anthropic_response.strip().split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            parts = line.rsplit("-", 1)  # sondan 1 kez ayır
                            if len(parts) == 2:
                                urun_adi_raw = parts[0].strip()
                                fiyat = parts[1].strip()
                                urun_adi = " ".join([p.strip() for p in
                                                     urun_adi_raw.split(
                                                         "-")])  # ürün adındaki '-' işaretlerini boşluk yap
                                append_to_menu_list(customer_code, urun_adi, fiyat, "")

                            else:

                                # Eğer line anlamlı bir hata veya uyarı mesajıysa, ürün adı boş, not sütununa yaz
                                append_to_menu_list(customer_code, "", "", line)
                else:
                    print(f"   Sayfa {page_num} dönüştürülemedi.")
                    append_to_menu_list(customer_code, "", "", "Görsel dönüştürme/medya tipi hatası")

        except Exception as e:
            print(f"   PDF işlenirken hata oluştu: {e}")
            append_to_menu_list(customer_code, "", "", f"PDF işleme hatası: {e}")

    # Drive linkli kayıtları işle
    drive_case(anthropic_prompt, qr_drive_linkli_kayitlar, client)

    # Web sitesi linkli kayıtlar - sadece not düş
    for index, row in qr_web_linkli_kayitlar.iterrows():
        customer_code = str(row['Müşteri Kodu']).strip()
        web_url = str(row['QR Verisi/Durumu']).strip()
        print(f"\n--- Web sitesi linki tespit edildi: Müşteri Kodu: {customer_code}, URL: {web_url} ---")
        print("   NOT: Bu link Firecrawl ile okunacak. Şu anda otomatik işleme eklenmedi.")
        append_to_menu_list(customer_code, "", "", "Web sitesi linki - Firecrawl ile okunacak (henüz otomatik değil)")

    print("\n Tüm işlemler tamamlandı. Menü listesi 'analysis.csv' dosyasına yazıldı.")

