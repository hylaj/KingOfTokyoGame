from django import forms

class JoinGameForm(forms.Form):
    game_code = forms.CharField(max_length=10, label="Game code")
    nickname = forms.CharField(max_length=50, label="Your nickname")
    monster = forms.ChoiceField(choices=[
        ("Gigazaur", "Gigazaur"),
        ("Meka Dragon", "Meka Dragon"),
        ("The Kraken", "The Kraken"),
        ("Cyber Bunny", "Cyber Bunny"),
        ("Alienoid", "Alienoid"),
        ("Space Penguin", "Space Penguin"),
    ], label="Monster")


class CreateGameForm(forms.Form):
    nickname = forms.CharField(max_length=50, label="Your nickname")
    monster = forms.ChoiceField(choices=[
        ("Gigazaur", "Gigazaur"),
        ("Meka Dragon", "Meka Dragon"),
        ("The Kraken", "The Kraken"),
        ("Cyber Bunny", "Cyber Bunny"),
        ("Alienoid", "Alienoid"),
        ("Space Penguin", "Space Penguin"),
    ], label="Monster")