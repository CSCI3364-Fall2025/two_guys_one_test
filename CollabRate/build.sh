#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate

# ── Seed the allauth SocialApp ───────────────────────────────────
python manage.py shell << 'EOF'
import os
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# 1) ensure the Site entry exists
SITE_ID = int(os.getenv("SITE_ID", "1"))
DOMAIN = os.getenv("RENDER_EXTERNAL_HOSTNAME", "mysite-8sga.onrender.com")
site, _ = Site.objects.get_or_create(
    id=SITE_ID,
    defaults={"domain": DOMAIN, "name": DOMAIN},
)

# 2) ensure the SocialApp exists (Google example)
app, created = SocialApp.objects.get_or_create(
    provider="google",
    defaults={
      "name":        "Google OAuth",
      "client_id":   os.environ["GOOGLE_CLIENT_ID"],
      "secret":      os.environ["GOOGLE_CLIENT_SECRET"],
    }
)
# 3) attach it to your site
app.sites.set([site])
app.save()
EOF