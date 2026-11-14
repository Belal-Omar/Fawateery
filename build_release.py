"""
build_release.py - بناء Fawateery.exe (ملف واحد) جاهز للتوزيع والتحديث عن بعد.

الاستخدام:
    .venv\\Scripts\\python.exe build_release.py

الناتج:  release_dist\\Fawateery.exe  (يُنسخ بعدها إلى مجلد Fawateery\\)
ملاحظة: نظام التحديث (updater.py) يستبدل Fawateery.exe كملف واحد، لذلك البناء onefile.
الإصدار يؤخذ من updater.CURRENT_VERSION (غيّره هناك قبل كل إصدار جديد).
"""
import os
import re
import sys
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


def current_version():
    src = open("updater.py", encoding="utf-8").read()
    return re.search(r'CURRENT_VERSION\s*=\s*"([\d.]+)"', src).group(1)


def write_version_file(ver):
    parts = (ver.split(".") + ["0", "0", "0", "0"])[:4]
    tup = ", ".join(parts)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({tup}), prodvers=({tup}), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Fawateery'),
      StringStruct('FileDescription', 'Fawateery Accounting'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', 'Fawateery'),
      StringStruct('OriginalFilename', 'Fawateery.exe'),
      StringStruct('ProductName', 'Fawateery'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    os.makedirs("release_build", exist_ok=True)
    path = os.path.join("release_build", "version_info.txt")
    open(path, "w", encoding="utf-8").write(content)
    return os.path.abspath(path)


def main():
    ver = current_version()
    print(f"== Building Fawateery v{ver}")
    vfile = write_version_file(ver)

    data = []
    for src, dst in [
        ("Amiri/Amiri-Regular.ttf", "Amiri"),
        ("Amiri/Amiri-Bold.ttf", "Amiri"),
        ("fawateery_icon.ico", "."),
        ("fawateery_icon_256.png", "."),
        ("fawateery_icon_128.png", "."),
        ("fawateery_icon_64.png", "."),
        ("أيقونة إف للحسابات والنمو.png", "."),
    ]:
        if os.path.exists(src):
            data += ["--add-data", f"{os.path.abspath(src)}{os.pathsep}{dst}"]
        else:
            print("!! missing data file:", src)

    hidden = ["arabic_reshaper", "bidi.algorithm", "fpdf", "pandas", "openpyxl", "sqlite3",
              "PIL", "PIL.ImageTk", "PIL._tkinter_finder", "tkcalendar", "qrcode", "tkinter",
              "matplotlib.backends.backend_tkagg", "matplotlib.backends.backend_agg",
              "babel.numbers", "selftest_ui", "arabic_entry_fix", "updater", "icon_manager",
              "tafqeet", "invoices_module", "employees", "transactions", "projects", "reports",
              "company_settings", "database", "accounts_receivable_module",
              "accounts_payable_module", "treasury_module", "customer_project_module",
              "authorizations_module", "central_refresh", "classic_pdf_template", "customers"]
    hid = []
    for h in hidden:
        hid += ["--hidden-import", h]

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", "Fawateery", "--icon", os.path.abspath("fawateery_icon.ico"),
           "--version-file", vfile,
           "--distpath", "release_dist", "--workpath", os.path.join("release_build", "work"),
           "--specpath", "release_build"] + data + hid + ["main.py"]
    print(" ".join(cmd[:8]), "...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)
    out = os.path.join("release_dist", "Fawateery.exe")
    print("== Done:", out, round(os.path.getsize(out) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()

