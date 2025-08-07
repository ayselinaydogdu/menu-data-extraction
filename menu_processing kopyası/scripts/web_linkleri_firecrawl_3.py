import asyncio
import csv
from firecrawl import AsyncFirecrawlApp, ScrapeOptions
from anthropic import Anthropic

FIRECRAWL_API_KEY = "fc-584a0abdc1a7470ca790738b0fea1a70"
ANTHROPIC_API_KEY = "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"

client = Anthropic(api_key=ANTHROPIC_API_KEY)

async def process_link(url, musteri_kodu):
    app = AsyncFirecrawlApp(api_key=FIRECRAWL_API_KEY)
    response = await app.crawl_url(
        url=url,
        limit=30,       # menüdeki kategorilerin adedine göre arttırılabilir, eksik ürün listelememk adına
        scrape_options=ScrapeOptions(
            formats=['markdown'],
            onlyMainContent=True,
            parsePDF=True,
            maxAge=14400000
        )
    )

    markdown_texts = [doc.markdown for doc in response.data if doc.markdown]
    full_markdown = "\n\n".join(markdown_texts)

    prompt = f"""
Aşağıda bir restoran menüsünden alınmış markdown formatında ham veri var.  
Lütfen sadece ürün adları ve fiyatlarını şu formatta listele:  
Ürün Adı (hacim belirtilmişse hacim değeri) - Fiyat

Ham veri:  
{full_markdown}
"""

    print(f"\n--- Menü verisi işleniyor ({musteri_kodu}) ---")
    response_llm = client.messages.create(
        model="claude-opus-4-20250514",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=6000,             # menüdeki ürünlerin fazlalılığna göre bu kısım arttırılabilir, eksik ürün listelememek adına
        temperature=0,
    )

    await asyncio.sleep(5)

    extracted = response_llm.content[0].text.strip()
    print(f"\n---- Ayıklanan Ürünler ----")
    print(extracted)

    extracted_rows = []
    unique_products = set()
    for line in extracted.splitlines():
        line = line.strip()
        if " - " in line and not any(k in line.lower() for k in ["ürün adı", "fiyat", "bilgisi", "adet", ":"]):
            try:
                urun_adi, fiyat = map(str.strip, line.split(" - ", 1))
                key = (urun_adi.lower(), fiyat)
                if key not in unique_products and fiyat.lower() != "fiyat belirtilmemiş":
                    unique_products.add(key)
                    extracted_rows.append([urun_adi, fiyat, musteri_kodu])
                    print(f"{urun_adi} - {fiyat}")
            except ValueError:
                continue

    return extracted_rows

async def main():
    target_customer_code = None

    # 1) analysis.csv'de "firecrawl ile okunacak" olan ilk satırı bul
    with open("analysis.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            note = row.get("Note", "").lower()
            if "firecrawl ile okunacak" in note:
                target_customer_code = row.get("Customer Code", "").strip()
                if target_customer_code:
                    break

    if not target_customer_code:
        print("Firecrawl ile işlenecek müşteri kodu bulunamadı.")
        return

    print(f"Firecrawl ile işlenecek müşteri kodu: {target_customer_code}")

    # 2) qr_links_musteri_kodlari.csv'den bu müşteri kodunun linkini bulalım
    url = None
    with open("qr_links_musteri_kodlari.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Müşteri Kodu", "").strip() == target_customer_code:
                url = row.get("QR Verisi/Durumu", "").strip()
                break

    if not url or url.lower().startswith("görsel qr değil"):
        print(f"{target_customer_code} için uygun link bulunamadı veya geçerli değil: {url}")
        return

    print(f"{target_customer_code} için bulunan link: {url}")

    # 3) Firecrawl işlemini yapalım
    try:
        results = await process_link(url, target_customer_code)
    except Exception as e:
        print(f"Firecrawl sırasında hata oluştu: {e}")
        results = []

    # 4) Sonuçları firecrawl_results.csv dosyasına yazalım
    with open("firecrawl_results.csv", "w", newline="", encoding="utf-8") as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(["Ürün Adı", "Fiyat", "Müşteri Kodu"])
        if results:
            writer.writerows(results)

    print(" İşlem tamamlandı, sonuçlar 'firecrawl_results.csv' dosyasına yazıldı.")

if __name__ == "__main__":
    asyncio.run(main())
