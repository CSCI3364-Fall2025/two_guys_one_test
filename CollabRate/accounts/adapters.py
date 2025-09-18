from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

ALLOWED_DOMAIN = "bc.edu"

class BCSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        email = sociallogin.user.email.lower() if sociallogin.user.email else ""
        # Only allow signup if the email ends with "@bc.edu"
        if not email.endswith(f"@{ALLOWED_DOMAIN}"):
            return False
        return super().is_open_for_signup(request, sociallogin)
