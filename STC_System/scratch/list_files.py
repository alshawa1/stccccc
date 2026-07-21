import os, sys
sys.stdout.reconfigure(encoding='utf-8')
folder = r'c:\Users\dell\Downloads\فايلات مهاره'
files = os.listdir(folder)
for f in files:
    if f.endswith('.xlsx'):
        print(repr(f))
