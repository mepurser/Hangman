import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    rating = ndb.IntegerProperty()

    def to_form(self):
        return RankingForm(user_name=self.name,
                           rating=self.rating)

    def update_rating(self, games):
        """
        Creates a player rating normalizing the number of games
        Golf rules: lower the score the better
        There is an additional 3 point penalty for games lost
        Players with no games won are unrated with rating -1
        """
        guesses = 0
        gamesWon = 0
        gamesLost = 0
        for game in games:
            guesses = guesses + game.attempts_allowed - game.attempts_remaining
            if game.game_over and not game.cancelled and \
                    game.attempts_remaining > 0:
                gamesWon = gamesWon + 1
            if game.attempts_remaining == game.attempts_allowed:
                gamesLost = gamesLost + 1

        if gamesWon:
            self.rating = guesses / gamesWon + (3 * gamesLost)
        else:
            self.rating = -1
        self.put()


class Game(ndb.Model):
    """Game object"""
    answer = ndb.StringProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    cancelled = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    guess_field = ndb.StringProperty(required=True)
    prev_guesses = ndb.JsonProperty()

    @classmethod
    def new_game(cls, user, answer, attempts):
        """Creates and returns a new game"""
        if len(answer) < 2:
            raise ValueError('Answer must be more than one letter')
        else:
            guess_field = ''
            for x in answer:
                guess_field += '*'
        game = Game(user=user,
                    answer=answer,
                    guess_field=guess_field,
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    game_over=False,
                    cancelled=False,
                    prev_guesses=[])
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.cancelled = self.cancelled
        form.message = message
        form.guess_field = self.guess_field
        return form

    def to_history_form(self):
        """Returns history of game"""
        form = HistoryForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.prev_guesses = GuessListForms(
            items=[self.to_prevguesses_form(guess)
                   for guess in self.prev_guesses])
        return form

    def to_prevguesses_form(self, guess):
        return GuessListForm(guess=guess)

    def update_guess_field(self, new_guess_field):
        self.guess_field = new_guess_field
        self.put()

    def add_to_guesslist(self, guess):
        self.prev_guesses.append(guess)

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=self.attempts_allowed - self.attempts_remaining)
        score.put()

    def cancel_game(self):
        """Cancels the game - won is always False."""
        """Game is not added to the scoreboard"""
        self.game_over = True
        self.cancelled = True
        self.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guesses = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guesses=self.guesses)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    cancelled = messages.BooleanField(4, required=True)
    message = messages.StringField(5, required=True)
    user_name = messages.StringField(6, required=True)
    guess_field = messages.StringField(7, required=True)


class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    answer_word = messages.StringField(2, required=True)
    # in Hangman, the total attempts is usually fixed, (by
    # the number of lines to draw the hanging) but the user
    # is allowed to specify the attempts here anyways.
    attempts = messages.IntegerField(3, default=9)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class RankingForm(messages.Message):
    """RankingForm for user rankings"""
    user_name = messages.StringField(1, required=True)
    rating = messages.IntegerField(2, required=True)


class RankingForms(messages.Message):
    """Return multiple RankingForms"""
    items = messages.MessageField(RankingForm, 1, repeated=True)


class GuessListForm(messages.Message):
    guess = messages.StringField(1, required=True)


class GuessListForms(messages.Message):
    items = messages.MessageField(GuessListForm, 1, repeated=True)


class HistoryForm(messages.Message):
    urlsafe_key = messages.StringField(1, required=True)
    user_name = messages.StringField(2, required=True)
    prev_guesses = messages.MessageField(GuessListForms, 3)
