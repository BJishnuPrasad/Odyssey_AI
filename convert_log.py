import os

if os.path.exists("pip_list.log"):
    # Read UTF-16LE as printed by PowerShell redirection
    try:
        with open("pip_list.log", "r", encoding="utf-16") as f:
            content = f.read()
    except Exception:
        with open("pip_list.log", "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    with open("pip_list_utf8.log", "w", encoding="utf-8") as f:
        f.write(content)
    print("Converted!")
else:
    print("pip_list.log not found")
