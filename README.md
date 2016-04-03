# Full Stack Nanodegree Project 4 Refresh

##Game Description:
Hangman is a simple word guessing game. Each game begins with an 'answer'
specified by a user (who is not the player). 'Guesses' can be a character in
the word or a word to guess the answer itself. If a guessed letter is in the
answer, 'guess_field' will be shown to display the length of the answer and
the characters that have been successfully guessed. If the whole word is guessed,
the player wins. If a guess is wrong, the player is notified and the attempts
remaining are decremented. If the word is guessed successfully or the remaining
attempts are zero, the game is over. Many different Hangman games can be played
by many different Users at any given time. Each game can be retrieved or played 
by using the path parameter `urlsafe_game_key`. The default number of attempts
is nine. This is usually fixed in a game like Hangman, but the ability to alter
this number has been preserved.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, answer, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Answer must be at least
    two characters. Also adds a task to a task queue to update the average moves
    remaining for active games.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.
    
 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
 - **get_active_game_count**
    - Path: 'games/active'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key.

- **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms
    - Description: Returns a GameForm for all of a particular user's active games.
    Does not report inactive games.

- **cancel_game**
    - Path: 'games/cancel/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key
    - Returns: GameForm
    - Description: Cancels an active game without posting to scoreboard. Makes
    no change to an inactive game.

- **get_high_scores**
    - Path: 'leaderboard'
    - Method: GET
    - Parameters: [maxScores]
    - Returns: ScoreForms
    - Description: Returns a leaderboard with top scores. Optionally limits
    number of results reported as per maxScores parameter.

- **get_user_rankings**
    - Path: 'ranking'
    - Method: GET
    - Parameters: none
    - Returns: RankingForms
    - Description: Update the ranking of each player (according to formula)
    and reports players by rank.

- **get_game_history**
    - Path: 'game/history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: HistoryForm
    - Description: Returns all the unique moves in a single game.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **NewGameForm**
    - Used to create a new game (user_name, answer, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **RankingForm**
    - User name and their rating.
 - **RankingForms**
    - Multiple RankingForm container.
 - **GuessListForm**
    - A guess from a particular turn in a game.
 - **GuessListForms**
    - Multiple GuessListForm container.
 - **HistoryForm**
    - User name, game and GuessListForms.