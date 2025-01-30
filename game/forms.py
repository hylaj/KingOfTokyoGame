from django import forms
from .data import MONSTERS



class JoinGameForm(forms.Form):
    game_code = forms.CharField(max_length=10, label="Game code", widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-light'}))
    nickname = forms.CharField(max_length=50, label="Nickname", widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-light'}))
    monster = forms.ChoiceField(
        choices=[(key, monster.name) for key, monster in MONSTERS.items()],
        label="Monster",
        widget=forms.Select(attrs={'class': 'form-select bg-dark text-light'})
    )



class CreateGameForm(forms.Form):
    nickname = forms.CharField(max_length=50, label="Nickname", widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-light'}))
    monster = forms.ChoiceField(
        choices=[(key, monster.name) for key, monster in MONSTERS.items()],
        label="Monster",
        widget=forms.Select(attrs={'class': 'form-select bg-dark text-light'})
    )

