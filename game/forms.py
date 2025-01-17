from django import forms
from .data import MONSTERS



class JoinGameForm(forms.Form):
    game_code = forms.CharField(max_length=10, label="Game code")
    nickname = forms.CharField(max_length=50, label="Your nickname")
    monster = forms.ChoiceField(
        choices=[(key, monster.name) for key, monster in MONSTERS.items()],
        label="Monster"
    )


class CreateGameForm(forms.Form):
    nickname = forms.CharField(max_length=50, label="Your nickname")
    monster = forms.ChoiceField(
        choices=[(key, monster.name) for key, monster in MONSTERS.items()],
        label="Monster"
    )
