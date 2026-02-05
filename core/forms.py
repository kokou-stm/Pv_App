from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Action


class UserRegistrationForm(UserCreationForm):
    """
    Formulaire d'inscription personnalisé.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_validated = False  # Ensure user is not validated by default
        if commit:
            user.save()
        return user


class ActionForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier des actions.
    """
    class Meta:
        model = Action
        fields = ['categorie', 'description', 'cause', 'personnes_impliquees', 'statut', 'suivi']
        widgets = {
            'categorie': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Décrivez l\'action effectuée en détail...',
                'required': True
            }),
            'cause': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Cause supposée ou identifiée (optionnel)...'
            }),
            'personnes_impliquees': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Noms des personnes impliquées (optionnel)...',
                'data-mention': 'true'  # Enable @mention autocomplete
            }),
            'statut': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'suivi': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'categorie': 'Catégorie',
            'description': 'Description de l\'action',
            'cause': 'Cause supposée ou identifiée',
            'personnes_impliquees': 'Personnes impliquées',
            'statut': 'Statut',
            'suivi': 'Nécessite un suivi'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = True
        self.fields['categorie'].required = True
        self.fields['statut'].required = True

