import os

# GitHub kişisel erişim token'ı ortam değişkeninden okunur: export GITHUB_TOKEN=...
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
