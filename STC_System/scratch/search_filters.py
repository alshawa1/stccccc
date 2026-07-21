import sys
sys.stdout.reconfigure(encoding='utf-8')

import os

workspace_dir = r"c:\Users\dell\Downloads\فايلات مهاره\STC_System"

print("Searching for allowed_sups or supervisor filter in all python files:")
for root, dirs, files in os.walk(workspace_dir):
    for filename in files:
        if filename.endswith(".py") and "__pycache__" not in root:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "allowed_sups" in content or "لمياء" in content:
                        print(f"Found in {os.path.relpath(filepath, workspace_dir)}:")
                        for line in content.splitlines():
                            if "allowed_sups" in line or "لمياء" in line or "المشرف" in line:
                                print(f"  {line}")
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
