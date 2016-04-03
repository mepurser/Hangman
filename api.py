"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, RankingForm, RankingForms, HistoryForm
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
LIST_REQUEST = endpoints.ResourceContainer(
    number_of_results=messages.IntegerField(1))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game.new_game(user.key, request.answer_word,
                                 request.attempts)
        except ValueError:
            raise endpoints.BadRequestException('Answer must be more '
                                                'than one letter!')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Hangman!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game.game_over:
            return game.to_form('Game already over!')
        # if a guess has already been made, the user will be alerted
        # and will not be penalized a guess
        if request.guess in game.prev_guesses:
            return game.to_form('You already guessed ' + request.guess)
        # user can enter either a letter or a word into the guess field.
        # if letter, check to see if letter is in word or not.
        # if word, check to see if word matches answer.
        if len(request.guess) == 0:
            raise endpoints.BadRequestException('Guess cannot be '
                                                'blank!')
        elif len(request.guess) == 1:
            # if letter guess is successful, show successful guesses
            # in guess_field
            if request.guess in game.answer:
                i = 0
                new_guess_field = ''
                while i < len(game.answer):
                    if request.guess == game.answer[i]:
                        new_guess_field += request.guess
                    elif game.guess_field[i] == '*':
                        new_guess_field += '*'
                    else:
                        new_guess_field += game.guess_field[i]
                    i += 1
                game.update_guess_field(new_guess_field)
                # if there are no more *'s, then the word has been guessed
                if '*' in new_guess_field:
                    msg = 'You got one! Keep guessing: ' + new_guess_field
                    game.add_to_guesslist(request.guess)
                else:
                    msg = 'You win! The answer is: ' + new_guess_field
                    game.end_game(True)
            else:
                msg = 'Nope! ' + request.guess + ' is not in the answer. ' \
                      'Keep guessing: ' + game.guess_field
                game.add_to_guesslist(request.guess)
                game.attempts_remaining -= 1
        else:
            if request.guess == game.answer:
                msg = 'Hooray! You win! The answer is: ' + game.answer
                game.end_game(True)
            else:
                msg = 'Nope! ' + request.guess + ' is not the answer. ' \
                      'Keep guessing: ' + game.guess_field
                game.add_to_guesslist(request.guess)
                game.attempts_remaining -= 1

        if game.attempts_remaining < 1:
            game.end_game(False)
            return game.to_form('Game over!')
        else:
            game.put()
            return game.to_form(msg)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(
            MEMCACHE_MOVES_REMAINING) or '')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Get all active games for a user"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        games = Game.query(Game.user == user.key, Game.game_over == False)
        return GameForms(items=[game.to_form('temp') for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """Cancel a game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            msg = 'This game is already over.'
        else:
            game.cancel_game()
            msg = 'GAME CANCELLED!'
        return game.to_form(msg)

    @endpoints.method(request_message=LIST_REQUEST,
                      response_message=ScoreForms,
                      path='leaderboard',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return all scores from highest to lowest"""
        maxScores = request.number_of_results
        scores = Score.query().order(Score.guesses).fetch(maxScores)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(request_message=LIST_REQUEST,
                      response_message=RankingForms,
                      path='ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Get rankings of all users"""
        users = User.query()
        for user in users:
            user_games = Game.query(Game.user == user.key,
                                    Game.game_over == True)
            user.update_rating(user_games)
        return RankingForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=HistoryForm,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Get previous guesses of a particular game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return game.to_history_form()

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                           for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'
                         .format(average))


api = endpoints.api_server([HangmanApi])
