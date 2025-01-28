from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from .forms import JoinGameForm, CreateGameForm
from django.template.loader import render_to_string
from django.http import HttpResponse
from .data import MONSTERS, Games, Player, DICE, Die
from collections import Counter
from django.utils.crypto import get_random_string
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

            return redirect("wait_for_game")
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

                return redirect("wait_for_game")

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
                return redirect("gameplay")
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

def get_game_and_player(request):
    """
    Pobiera grę i gracza z sesji. Rzuca wyjątek, jeśli gra lub gracz nie istnieją.
    """
    game_code = request.session.get("game_code")
    game = Games.get_game(game_code)
    if not game:
        raise ObjectDoesNotExist("Game not found")

    player_id = request.session.get("player_id")
    player = next((player for player in game.players if str(player.id) == player_id), None)
    if not player:
        raise ObjectDoesNotExist("Player not found")

    return game, player

def wait_for_game(request):
    try:
        game, current_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

    if game.status == "playing":
        return redirect("gameplay")

    return render(request, "wait_for_game.html", {
        "players": game.players,
        "game_code": game.game_code,
        "current_player": current_player
    })

def check_game_status(request):
    try:
        game,player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

    return JsonResponse({"status": game.status})


def get_players(request):
    game, player = get_game_and_player(request)
    players_html = render_to_string("partials/players_list.html", {"players": game.players})
    return HttpResponse(players_html)


def start_game(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

    if len(game.players) < 2: #Musi być minimum 2 graczy, aby rozpocząć rozgrywkę
        messages.error(request, "Too few players.")
        return redirect("wait_for_game")
    if str(game.players[0].id) == str(viewing_player.id):  # Tylko twórca gry może ją rozpocząć
        game.start_game()
        return redirect('gameplay')


def gameplay(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

    if game.status != 'playing':
        if game.status == 'waiting':
            messages.error(request, "This game has not started yet")
            return redirect("wait_for_game")
        elif game.status == 'finished':
            messages.error(request, "This game is finished")
            return redirect("end_game")

    current_player = game.get_current_player()


    if str(current_player.id) != str(viewing_player.id):
        messages.error(request, "Not your turn")
        return redirect("gameplay_view")

    if 'form_token' not in request.session:
        request.session['form_token'] = get_random_string(length=32)

    if request.method == 'POST':
        submitted_token = request.POST.get('form_token')
        # Sprawdzamy, czy token jest zgodny z tym w sesji
        if submitted_token != request.session.get('form_token'):
            messages.warning(request, "Please do not refresh the page while playing your turn.")
            return redirect('gameplay')

        if 'roll_dice_btn' in request.POST:
            current_player.roll_player_dice()
            game.show_roll = False
            if current_player.roll_count == 3:
                current_player.kept_dice.extend(current_player.dice_result)
                current_player.displayed_dice= []
            if game.tokyo_player is None and any(dice.name == "attack" for dice in current_player.dice_result): #Pierwszy gracz, który na początku gry wyrzuci co najmniej jeden symbol ataku przemieszcza swój pionek do Tokio
                game.tokyo_player = current_player
                current_player.in_tokyo = True
                current_player.gain_victory(1) #Gracz zyskuje 1 pkt kiedy wchodzi do Tokio
                if game.check_end_game():
                    return redirect("end_game")


        if 'save_dice_btn' in request.POST:
            selected_dice_names = request.POST.getlist("kept_dice", [])
            selected_dice = []
            for name in selected_dice_names:
                # Znajdujemy kostkę, która pasuje do każdego wybranego nazwy
                die = next((d for d in DICE if d.name == name), None)
                if die:
                    selected_dice.append(die)
            current_player.kept_dice.extend(selected_dice)
            game.show_roll = True

            counter1=Counter(current_player.dice_result)
            counter2=Counter(selected_dice)
            result_counter=counter1-counter2
            current_player.displayed_dice=list(result_counter.elements())

        if 'buy_card' in request.POST:
            card_id = int(request.POST.get('card_id'))
            card = game.available_cards[card_id]
            try:
                viewing_player.buy_card(card, game)
            except Exception as e:
                messages.error(request, str(e))

        del request.session['form_token']
        request.session['form_token'] = get_random_string(length=32)


    if len(current_player.kept_dice) == 6 and current_player.saved_results == False:
        current_player.save_results(game)
        current_player.saved_results = True

    if game.check_end_game():
        return redirect("end_game")

    if not current_player.is_active:
        game.next_turn()
        return redirect("eliminated_player_view")

    # Resetowanie tokenu po jego wykorzystaniu


    return render(request, 'gameplay.html',{
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.displayed_dice,
        'selected_dice': current_player.kept_dice,
        'show_roll': game.show_roll,
        'game': game,
        "available_cards": game.available_cards,
        "form_token": request.session.get('form_token'),

    })

def gameplay_view(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")
    current_player = game.get_current_player()

    if game.check_end_game():
        return redirect("end_game")
    if not viewing_player.is_active:
            return redirect("eliminated_player_view")
    if current_player==viewing_player:
        return redirect('gameplay')

    return render(request, 'gameplay_view.html',{
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.displayed_dice,
        'selected_dice': current_player.kept_dice,
        'game': game,
        "available_cards": game.available_cards,
    })

def get_gameplay_data(request):
    game, viewing_player = get_game_and_player(request)

    current_player = game.get_current_player()

    gameplay_data_html = render_to_string("partials/gameplay_data.html", {
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.displayed_dice,
        'selected_dice': current_player.kept_dice,
        'game': game,
        "available_cards": game.available_cards,
    })
    return HttpResponse(gameplay_data_html)

def get_tokyo_player(request):
    game, viewing_player = get_game_and_player(request)
    current_player = game.get_current_player()
    tokyo_player_html=render_to_string("partials/get_tokyo_player.html", {
        "game": game,
        "current_player": current_player,
    })
    return HttpResponse(tokyo_player_html)

def get_players_outside_tokyo(request):
    game, viewing_player = get_game_and_player(request)
    current_player = game.get_current_player()
    tokyo_player_html=render_to_string("partials/get_players_outside_tokyo.html", {
        "game": game,
        "current_player": current_player,
    })
    return HttpResponse(tokyo_player_html)

def leave_tokyo(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

#gracz może opuścić Tokio po ataku przez innego gracza w trakcie tury innego gracza lub na początku własnej tury, przed rzutem kostkami
    if viewing_player.was_attacked and viewing_player.roll_count == 0 and viewing_player != game.attacking_player:
        viewing_player.in_tokyo = False
        game.attacking_player.in_tokyo = True
        game.tokyo_player = game.attacking_player
        game.attacking_player.gain_victory(1) #Gracz zyskuje 1 pkt za wejscie do Tokio
        viewing_player.was_attacked = False
        game.add_log(f"{viewing_player.nickname} left Tokyo. {game.attacking_player.nickname} enters Tokyo.")

    else:
        messages.warning(request, "You can't leave Tokyo now")
    return redirect('gameplay_view')


def eliminated_player_view(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

    if viewing_player.in_tokyo:
        viewing_player.in_tokyo = False
        game.attacking_player.in_tokyo = True
        game.tokyo_player = game.attacking_player
        game.attacking_player.gain_victory(1)
        viewing_player.was_attacked = False


    if game.check_end_game():
        return redirect("end_game")

    return render(request, 'eliminated_player_view.html', {
        'game': game,
    })


def check_current_player(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")
    current_player = game.get_current_player()

    return JsonResponse({
        "currentPlayer": str(current_player.id),
        "viewingPlayer": str(viewing_player.id),
        "viewingPlayer_isActive": viewing_player.is_active,
    })

def end_turn(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")
    current_player = game.get_current_player()

    if len(current_player.kept_dice) == 6:
        game.next_turn()
        if game.check_end_game():
            return redirect("end_game")

        return redirect('gameplay_view')
    else:
        messages.info(request, "Roll the dice to complete your turn.")
        return redirect('gameplay')


def end_game(request):
    try:
        game, viewing_player = get_game_and_player(request)
    except ObjectDoesNotExist as e:
        messages.error(request, str(e))
        return redirect("home")

    game.status = 'finished'

    return render(request, "end_game.html", {
        "game": game,
        "viewing_player": viewing_player,
    })









