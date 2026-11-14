"""
publish_update.py - أداة نشر التحديثات الأوتوماتيكية لبرنامج فواتيري (بأمر واحد)
--------------------------------------------------------------------------------
الاستخدام:
    .venv\\Scripts\\python.exe publish_update.py
    أو مع تحديد الإصدار والوصف مباشرة:
    .venv\\Scripts\\python.exe publish_update.py 1.0.3 "إضافة ميزة جديدة وإصلاح بعض الأخطاء"

ماذا يفعل هذا السكربت بالترتيب؟
1. يقرأ رقم الإصدار الجديد وسجل التغييرات (أو يحدثهما في updater.py و version.json).
2. يبني ملف Fawateery.exe الجديد عبر build_release.py.
3. يشغّل الفحص الذاتي الآلي (--selftest) على الـ EXE للتأكد من سلامة كل الأزرار والوظائف.
4. ينسخ الـ EXE الجديد إلى مجلد Fawateery\\Fawateery.exe (مع حفظ نسخة احتياطية للقديم).
5. يرفع الكود المحدث وملف version.json إلى فرع main على GitHub.
6. ينشئ Release جديد على GitHub ويرفع بداخله ملف Fawateery.exe ليصل التحديث فوراً للعملاء.
"""

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
REPO = "Belal-Omar/Fawateery"


def update_version_files(new_ver=None, new_changelog=None):
    with open("version.json", "r", encoding="utf-8") as f:
        vdata = json.load(f)

    if new_ver:
        vdata["version"] = new_ver.lstrip("vV")
    ver = vdata["version"]
    vdata["release_date"] = datetime.now().strftime("%Y-%m-%d")
    vdata["download_url"] = f"https://github.com/{REPO}/releases/download/v{ver}/Fawateery.exe"
    if new_changelog:
        vdata["changelog"] = new_changelog

    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(vdata, f, ensure_ascii=False, indent=2)

    with open("updater.py", "r", encoding="utf-8") as f:
        up_code = f.read()
    up_code_new = re.sub(
        r'CURRENT_VERSION\s*=\s*"[^"]+"',
        f'CURRENT_VERSION = "{ver}"',
        up_code
    )
    if up_code_new != up_code:
        with open("updater.py", "w", encoding="utf-8") as f:
            f.write(up_code_new)

    return ver, vdata["changelog"]


def get_github_token():
    p = subprocess.Popen(
        ["git", "credential", "fill"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, _ = p.communicate("protocol=https\nhost=github.com\n\n")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("تعذر جلب رمز المصادقة من Git Credential Manager.")


def run_build_and_test():
    print("🔨 1/5 جاري بناء Fawateery.exe ...")
    r = subprocess.run([sys.executable, "build_release.py"])
    if r.returncode != 0:
        raise RuntimeError("فشل بناء ملف EXE!")

    exe_Built = os.path.join(ROOT, "release_dist", "Fawateery.exe")
    print("🧪 2/5 جاري تشغيل الفحص الذاتي الآلي على الـ EXE ...")
    tmp_dir = tempfile.mkdtemp(prefix="fw_pub_test_")
    appdata = os.path.join(tmp_dir, "appdata")
    os.makedirs(os.path.join(appdata, "Fawateery"), exist_ok=True)
    if os.path.exists("accounting.db"):
        shutil.copy2("accounting.db", os.path.join(appdata, "Fawateery", "accounting.db"))

    env = os.environ.copy()
    env["APPDATA"] = appdata
    env["FAWATEERY_VERSION_URL"] = "http://127.0.0.1:9/version.json"
    rep_path = os.path.join(tmp_dir, "report.json")
    p = subprocess.run([exe_Built, "--selftest", rep_path], cwd=tmp_dir, env=env, timeout=420)
    if p.returncode != 0:
        raise RuntimeError(f"فشل الفحص الذاتي! راجع التقرير: {rep_path}")
    print("✅ الفحص الذاتي نجح بالكامل (0 أخطاء).")

    print("📦 3/5 تحديث مجلد Fawateery\\Fawateery.exe ...")
    target_dir = os.path.join(ROOT, "Fawateery")
    os.makedirs(target_dir, exist_ok=True)
    target_exe = os.path.join(target_dir, "Fawateery.exe")
    if os.path.exists(target_exe):
        old_dir = os.path.join(target_dir, "_old_versions")
        os.makedirs(old_dir, exist_ok=True)
        shutil.copy2(target_exe, os.path.join(old_dir, f"Fawateery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.exe"))
    shutil.copy2(exe_Built, target_exe)
    return target_exe


def push_to_github_main(ver):
    print("☁️ 4/5 رفع الكود وملف version.json إلى فرع main على GitHub ...")
    clone_dir = os.path.join(tempfile.gettempdir(), "fw_repo_sync")
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir, ignore_errors=True)
    subprocess.run(["git", "clone", f"https://github.com/{REPO}.git", clone_dir], check=True)

    files = [
        "main.py", "selftest_ui.py", "updater.py", "arabic_entry_fix.py", "invoices_module.py",
        "invoices_fixed.py", "employees.py", "employees_new.py", "transactions.py", "projects.py",
        "reports.py", "company_settings.py", "database.py", "accounts_receivable_module.py",
        "accounts_payable_module.py", "treasury_module.py", "customer_project_module.py",
        "authorizations_module.py", "central_refresh.py", "icon_manager.py", "tafqeet.py",
        "classic_pdf_template.py", "customers.py", "build_release.py", "publish_update.py",
        "requirements.txt", "version.json", "fawateery_icon.ico", "fawateery_icon_256.png",
        "fawateery_icon_128.png", "fawateery_icon_64.png", "أيقونة إف للحسابات والنمو.png"
    ]
    for fn in files:
        if os.path.exists(fn):
            shutil.copy2(fn, os.path.join(clone_dir, fn))

    os.makedirs(os.path.join(clone_dir, "Amiri"), exist_ok=True)
    for fn in ("Amiri-Regular.ttf", "Amiri-Bold.ttf", "OFL.txt"):
        p = os.path.join("Amiri", fn)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(clone_dir, "Amiri", fn))

    dialogs_src = os.path.join("Fawateery", "dialogs")
    if os.path.isdir(dialogs_src):
        os.makedirs(os.path.join(clone_dir, "dialogs"), exist_ok=True)
        for fn in os.listdir(dialogs_src):
            if fn.endswith(".py"):
                shutil.copy2(os.path.join(dialogs_src, fn), os.path.join(clone_dir, "dialogs", fn))

    subprocess.run(["git", "add", "-A"], cwd=clone_dir, check=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=clone_dir, capture_output=True, text=True).stdout.strip()
    if status:
        subprocess.run(["git", "commit", "-m", f"Release v{ver}"], cwd=clone_dir, check=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=clone_dir, check=True)
        print("✅ تم تحديث فرع main على GitHub.")
    else:
        print("ℹ️ فرع main محدث بالفعل.")


def upload_release_asset(ver, changelog, exe_path):
    print(f"🚀 5/5 إنشاء Release v{ver} ورفع Fawateery.exe على GitHub ...")
    token = get_github_token()
    tag = f"v{ver}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Fawateery-Publisher/1.0",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}", headers=headers)
        with urllib.request.urlopen(req) as resp:
            rel = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            body = json.dumps({
                "tag_name": tag,
                "target_commitish": "main",
                "name": f"فواتيري - الإصدار {tag}",
                "body": changelog,
                "draft": False,
                "prerelease": False
            }).encode("utf-8")
            req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases",
                data=body,
                headers={**headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                rel = json.loads(resp.read().decode("utf-8"))
        else:
            raise

    for asset in rel.get("assets", []):
        if asset["name"] == "Fawateery.exe":
            req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}",
                headers=headers, method="DELETE"
            )
            urllib.request.urlopen(req).close()

    exe_size = os.path.getsize(exe_path)
    upload_url = rel["upload_url"].split("{")[0] + "?name=Fawateery.exe"
    with open(exe_path, "rb") as f:
        req = urllib.request.Request(
            upload_url, data=f,
            headers={**headers, "Content-Type": "application/octet-stream", "Content-Length": str(exe_size)},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            asset_info = json.loads(resp.read().decode("utf-8"))
            print("✅ اكتمل رفع الإصدار بنجاح!")
            print("🔗 رابط التنزيل المباشر للعملاء:", asset_info["browser_download_url"])


def main():
    new_ver = sys.argv[1] if len(sys.argv) > 1 else None
    new_log = sys.argv[2] if len(sys.argv) > 2 else None
    ver, changelog = update_version_files(new_ver, new_log)
    print(f"=== بدء نشر برنامج فواتيري الإصدار v{ver} ===")
    exe_path = run_build_and_test()
    push_to_github_main(ver)
    upload_release_asset(ver, changelog, exe_path)
    print(f"\n🎉 تم نشر الإصدار v{ver} بالكامل! سيصل إشعار التحديث تلقائياً لجميع العملاء عند تشغيل البرنامج.")


if __name__ == "__main__":
    main()

