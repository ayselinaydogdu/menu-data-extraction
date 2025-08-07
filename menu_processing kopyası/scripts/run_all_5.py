import subprocess
import os


def run_script(script_name):
    print(f"\nRunning {script_name}...")
    result = subprocess.run(["python", script_name], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"{script_name} finished successfully.")
    else:
        print(f"Error in {script_name}:")
        print(result.stderr)
        exit(1)


if __name__ == "__main__":
    scripts = [
        "decide_qr_or_not.py",
        "image_isNot_qr.py",
        "web_linkleri_firecrawl.py",
        "merge_csv_convertExcel.py"
    ]

    for script in scripts:
        run_script(script)

    print("\n✅ All scripts executed successfully.")
    print("📁 Final file created: Combined_Menu_List.xlsx")
