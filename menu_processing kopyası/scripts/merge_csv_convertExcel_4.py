import pandas as pd
import csv

# 1. CSV (ana liste)
df1 = pd.read_csv("analysis.csv")

# 2. CSV (yeni veriler)
df2 = pd.read_csv("firecrawl_results.csv", names=["Product Name", "Price", "Customer Code"], header=0)


# Note sütunu ekle, boş olarak
df2["Note"] = ""

# Birleştir
combined = pd.concat([df1, df2], ignore_index=True)

# Son CSV olarak kaydet
combined.to_csv("combined_menu_list.csv", index=False)


# CONVERT TO EXCEL

input_file = "combined_menu_list.csv"
output_file = " Combined_Menu_List.xlsx"

rows = []
with open(input_file, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader)  # başlıkları oku
    rows.append(headers)

    for row in reader:
        # Satırın uzunluğunu kontrol et, eksikse tamamla
        while len(row) < 4:
            row.append("")

        # Fiyat boşsa n/a yaz
        if not row[1].strip():
            row[1] = "n/a"

        rows.append(row)

# Pandas ile Excel'e yaz
df = pd.DataFrame(rows[1:], columns=rows[0])
df.to_excel(output_file, index=False)

print(f"Excel dosyası '{output_file}' olarak kaydedildi.")
