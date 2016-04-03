#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import HangmanApi

from models import User, Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """
        Send a reminder email to each User with an email about games.
        This sends each user one reminder daily if any active games. So if a
        user has two active games, she will receive only one email.
        Called every 24 hours using a cron job
        """
        app_id = app_identity.get_application_id()
        active_games = Game.query(Game.game_over == False)
        all_users = User.query(User.email != None)
        for user in all_users:
            for game in active_games:
                if user.key == game.user:
                    subject = 'This is a reminder!'
                    body = "Hello {}, you have at least one active" \
                        + "hangman game!".format(user.name)
                    # This will send test emails,
                    # the arguments to send_mail are:
                    # from, to, subject, body
                    mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                                   user.email,
                                   subject,
                                   body)
                    # once active game has been found for user, exit for loop
                    break


class UpdateAverageMovesRemaining(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        HangmanApi._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug=True)
