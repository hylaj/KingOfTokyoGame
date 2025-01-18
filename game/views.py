from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import JoinGameForm, CreateGameForm
from django.template.loader import render_to_string
from django.http import HttpResponse
from .data import MONSTERS, Games, Game, Player


def home(request):
    return render(request, 'home.html')

def game_rules(request):
    return render(request, 'game_rules.html')


def create_new_game(request):
    form = CreateGameForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            nickname = form.cleaned_data["nickname"]
            monster_key = form.cleaned_data["monster"]

            # Pobierz obiekt potwora
            chosen_monster = MONSTERS[monster_key]

            # Tworzenie nowej gry
            game = Games.create_game()
            request.session["game_code"] = game.game_code

            # Dodanie gracza jako pierwszego uczestnika
            new_player = Player(nickname, chosen_monster)
            game.add_player(new_player)
            request.session["player_id"] = str(new_player.id)

            return redirect("wait_for_game", game_code=game.game_code)
        else:
            messages.error(request, "Invalid form data. Please check your input.")

    return render(request, "create_game.html", {"form": form})

# Funkcja do obsługi formularza dołączania do gry
def create_form_join_game(request):
    form = JoinGameForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            game_code = form.cleaned_data["game_code"]
            nickname = form.cleaned_data["nickname"]
            monster_key = form.cleaned_data["monster"]

            # Pobierz obiekt potwora
            chosen_monster = MONSTERS[monster_key]

            # Sprawdzenie, czy gra istnieje
            game = Games.get_game(game_code)
            if not game:
                messages.error(request, 'Given game code does not exist')
            elif game.status == 'playing':
                messages.error(request, 'Game in progress. Cannot join.')
            elif game.status == 'finished':
                messages.error(request, 'Game is already finished. Cannot join.')
            elif len(game.players) >= 6:
                messages.error(request, "The game is already full.")
            elif any(player.nickname.lower() == nickname.lower() for player in game.players):
                messages.error(request, "The nickname is already taken in this game. Please choose another one.")
            elif any(player.monster == chosen_monster for player in game.players):
                messages.error(request, "The chosen monster is already taken.")
            else:
                # Dodanie gracza do gry
                new_player = Player(nickname, chosen_monster)
                game.add_player(new_player)
                request.session["player_id"] = str(new_player.id)
                request.session["game_code"] = game.game_code

                return redirect("wait_for_game", game_code=game.game_code)

    # Jeśli formularz nie jest poprawny lub wystąpił błąd, renderujemy stronę z błędami
    return render(request, "join_game.html", {"form": form})

#Ponowne dołączanie do gry
def rejoin_game(request):
    # Sprawdź, czy w sesji są zapisane dane gracza i gry
    player_id = request.session.get("player_id")
    game_code = request.session.get("game_code")

    if player_id and game_code:
        # Sprawdź, czy gra istnieje
        game = Games.get_game(game_code)
        if game:
            # Sprawdź, czy gracz jest częścią tej gry
            player = next((p for p in game.players if str(p.id) == player_id), None)
            if player:
                # Gracz i gra istnieją - przekieruj do gry
                return redirect("gameplay", game_code=game_code)
            else:
                # Jeśli gracz nie istnieje w grze, usuń dane z sesji
                del request.session["player_id"]
                del request.session["game_code"]
                messages.error(request, "Your session is invalid. Please join the game again.")
        else:
            # Jeśli gra nie istnieje, usuń dane z sesji
            del request.session["player_id"]
            del request.session["game_code"]
            messages.error(request, "The game does not exist. Please join a new game.")
    else:
        # Jeśli brakuje danych w sesji
        messages.error(request, "No active session found. Please join a game.")

    # Przekierowanie na stronę główną lub do formularza dołączenia
    return redirect("home")



def wait_for_game(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, 'Given game code does not exist')
        return redirect("home")
    if game.status == "playing":
        return redirect("gameplay", game_code=game_code)

    player_id = request.session.get("player_id")
    current_player = next((player for player in game.players if str(player.id) == player_id), None)

    return render(request, "wait_for_game.html", {
        "players": game.players,
        "game_code": game.game_code,
        "current_player": current_player
    })

def check_game_status(request):
    game_code=request.session.get('game_code')
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")
    return JsonResponse({"status": game.status})


def get_players(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    players_html = render_to_string("partials/players_list.html", {"players": game.players})
    return HttpResponse(players_html)


def start_game(request, game_code):
    game = Games.get_game(game_code)
    player_id = request.session.get("player_id")

    if not game:
        messages.error(request, "Game not found")
        return redirect("home")
    if len(game.players) < 2: #Musi być minimum 2 graczy, aby rozpocząć rozgrywkę
        messages.error(request, "Too few players.")
        return redirect("wait_for_game", game_code=game_code)
    if str(game.players[0].id) == player_id:  # Tylko twórca gry może ją rozpocząć
        game.start_game()
        return redirect('gameplay', game_code=game_code)


def gameplay(request, game_code):
    game = Games.get_game(game_code)

    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    if game.status != 'playing':
        if game.status == 'waiting':
            messages.error(request, "This game has not started yet")
            return redirect("wait_for_game", game_code=game_code)
        elif game.status == 'finished':
            messages.error(request, "This game is finished")
            return redirect("end_game")

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)
    current_player = game.get_current_player()

    if str(current_player.id) != str(viewing_player_id):
        messages.error(request, "Not your turn")
        return redirect("gameplay_view", game_code=game_code)

    if request.method == 'POST':
        if 'roll_dice_btn' in request.POST:
            current_player.roll_player_dice()
            game.show_roll = False
            if current_player.roll_count == 3:
                current_player.kept_dice.extend(current_player.dice_result)
            if game.tokyo_player is None and "attack" in current_player.dice_result: #Pierwszy gracz, który na początku gry wyrzuci co najmniej jeden symbol ataku przemieszcza swój pionek do Tokio
                game.tokyo_player = current_player
                current_player.in_tokyo = True
                current_player.gain_victory(1) #Gracz zyskuje 1 pkt kiedy wchodzi do Tokio
                if game.check_end_game():
                    return redirect("end_game")

        if 'save_dice_btn' in request.POST:
            selected_dice = request.POST.getlist("kept_dice", [])
            current_player.kept_dice.extend(selected_dice)
            game.show_roll = True

    if len(current_player.kept_dice) == 6:
        current_player.save_results(game)

    if game.check_end_game():
        return redirect("end_game")

    if not current_player.is_active:
            return redirect("eliminated_player_view")

    return render(request, 'gameplay.html',{
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.dice_result,
        'selected_dice': current_player.kept_dice,
        'show_roll': game.show_roll,
        'game': game,
    })

def gameplay_view(request, game_code):
    game = Games.get_game(game_code)

    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    if game.check_end_game():
        return redirect("end_game")

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)
    current_player = game.get_current_player()

    if not viewing_player.is_active:
            return redirect("eliminated_player_view")

    if current_player==viewing_player:
        return redirect('gameplay', game_code=game_code)

    return render(request, 'gameplay_view.html',{
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.dice_result,
        'selected_dice': current_player.kept_dice,
        'game': game,
    })

def get_gameplay_data(request, game_code):
    game = Games.get_game(game_code)

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)
    current_player = game.get_current_player()

    gameplay_data_html = render_to_string("partials/gameplay_data.html", {
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.dice_result,
        'selected_dice': current_player.kept_dice,
        'game': game,
    })
    return HttpResponse(gameplay_data_html)

def get_tokyo_player(request, game_code):
    game = Games.get_game(game_code)

    tokyo_player_html=render_to_string("partials/get_tokyo_player.html", {
        "game": game,
    })
    return HttpResponse(tokyo_player_html)


def leave_tokyo(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)

#gracz może opuścić Tokio po ataku przez innego gracza w trakcie tury innego gracza lub na początku własnej tury, przed rzutem kostkami
    if viewing_player.was_attacked and viewing_player.roll_count == 0:
        viewing_player.in_tokyo = False
        game.attacking_player.in_tokyo = True
        game.tokyo_player = game.attacking_player
        game.attacking_player.gain_victory(1) #Gracz zyskuje 1 pkt za wejscie do Tokio
        viewing_player.was_attacked = False
    else:
        messages.warning(request, "You can't leave Tokyo now")
    return redirect('gameplay_view', game_code=game_code)


def eliminated_player_view(request):
    game_code = request.session.get("game_code")
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")


    player_id = request.session.get("player_id")
    player = next((player for player in game.players if str(player.id) == player_id), None)

    if player.in_tokyo:
        player.in_tokyo = False
        game.attacking_player.in_tokyo = True
        game.tokyo_player = game.attacking_player
        game.attacking_player.gain_victory(1)
        player.was_attacked = False

    return render(request, 'eliminated_player_view.html', {
        'game': game,
    })




def check_current_player(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    current_player = game.get_current_player()
    current_player_id = str(current_player.id)
    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)

    return JsonResponse({
        "currentPlayer": current_player_id,
        "viewingPlayer": viewing_player_id,
        "viewingPlayer_isActive": viewing_player.is_active,
    })

def end_turn(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")
    current_player = game.get_current_player()
    if len(current_player.kept_dice) == 6:
        game.next_turn()

        if game.check_end_game():
            return redirect("end_game")

        return redirect('gameplay_view', game_code=game_code)
    else:
        messages.info(request, "Roll the dice to complete your turn.")
        return redirect('gameplay', game_code=game_code)


def end_game(request):
    game_code=request.session.get("game_code")
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    game.status = 'finished'

    return render(request, "end_game.html", {
        "game": game,
    })









