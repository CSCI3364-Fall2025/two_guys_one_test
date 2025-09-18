from allauth.socialaccount.forms import SignupForm
from django import forms
from .models import CustomUser

class CustomSocialSignupForm(SignupForm):
    user_type = forms.ChoiceField(
        choices=[(CustomUser.STUDENT, 'Student'), (CustomUser.PROFESSOR, 'Professor')],
        required=True,
        label="I am a",
        widget=forms.HiddenInput()
    )

    def save(self, request):
        user = super(CustomSocialSignupForm, self).save(request)
        user.user_type = self.cleaned_data.get('user_type')
        user.save()
        return user