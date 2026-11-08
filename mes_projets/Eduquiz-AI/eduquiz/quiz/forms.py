from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Document, Quiz


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(
                attrs={
                    'placeholder': 'Nom d’utilisateur',
                    'class': 'input-field',
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'placeholder': 'Email',
                    'class': 'input-field',
                }
            ),
            'password1': forms.PasswordInput(
                attrs={
                    'placeholder': 'Mot de passe',
                    'class': 'input-field',
                }
            ),
            'password2': forms.PasswordInput(
                attrs={
                    'placeholder': 'Confirme le mot de passe',
                    'class': 'input-field',
                }
            ),
        }


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={'placeholder': 'Nom d’utilisateur', 'class': 'input-field'}
        )
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={'placeholder': 'Mot de passe', 'class': 'input-field'}
        ),
    )


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'placeholder': 'Titre du cours, par exemple HTML',
                    'class': 'input-field',
                }
            ),
            'file': forms.ClearableFileInput(
                attrs={'accept': '.pdf', 'class': 'input-field'}
            ),
        }

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        max_size = 15 * 1024 * 1024
        if uploaded.size > max_size:
            raise forms.ValidationError('Le PDF ne doit pas dépasser 15 Mo.')
        if not uploaded.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Seuls les fichiers PDF sont acceptés.')
        return uploaded


class QuizCreateForm(forms.ModelForm):
    question_count = forms.ChoiceField(
        choices=[
            ('5', '5 questions'),
            ('10', '10 questions'),
            ('15', '15 questions'),
            ('20', '20 questions'),
            ('30', '30 questions'),
            ('50', '50 questions'),
        ],
        initial='10',
        label='Nombre de questions',
    )
    level = forms.ChoiceField(
        choices=Quiz._meta.get_field('level').choices,
        initial='easy',
        label='Niveau',
    )

    class Meta:
        model = Quiz
        fields = ['question_count', 'level']