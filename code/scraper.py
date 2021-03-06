from __future__ import print_function

from utilities import Utilities
from exception_helper import ExceptionHelper
from comment import Comment
from db_controller import DB_Controller

import json
import sys
import os
import click
import praw
import requests

from time import sleep


class Scraper:
    ## Globals
    REDDIT_CFG_NAME = "reddit.json"
    REDDIT_CFG_PATH = Utilities.build_path_from_config(REDDIT_CFG_NAME)
    COMMENTS_TABLE = "comments"
    COMMENTS_COLUMNS = ["post_id", "author", "time_created", "flair", "body"]


    def __init__(self, db_controller=None, **kwargs):
        self.static = Scraper

        ## Init the exception helper
        self.exception_helper = ExceptionHelper(log_time=True, std_stream=sys.stderr)

        ## Hard limit to attempt to stream comments (so the script doesn't
        ##  just endlessly accomplish nothing)
        self._attempts = 0

        ## Get the config data for the reddit instance
        self.reddit_cfg = Utilities.load_json(self.static.REDDIT_CFG_PATH)

        ## Get Reddit instance
        try:
            self.reddit = praw.Reddit(client_id=self.reddit_cfg["id"],
                                      client_secret=self.reddit_cfg["secret"],
                                      user_agent=self.reddit_cfg["useragent"],
                                      username=self.reddit_cfg["username"],
                                      password=self.reddit_cfg["password"])
        except Exception as e:
            self.exception_helper.print(e, "Unexpected error when getting Reddit instance.\n", exit=True)

        ## Get Subreddit instance
        try:
            self.subreddit = self.reddit.subreddit(self.reddit_cfg["subreddit"])
        except Exception as e:
            self.exception_helper.print(e, "Unexpected error when getting subreddit instance.\n", exit=True)

        ## Save the db_controller, or instantiate it if necessary
        if(not db_controller):
            db_controller = DB_Controller(**kwargs)
        self.db = db_controller

        ## Start parsing the new comment stream
        self.exception_helper.make_robust(self.stream_comments, (requests.RequestException, Exception), self.exception_helper.print_stderr, self.exception_helper.print_stderr)

    ## Methods

    def stream_comments(self):
        for comment in self.subreddit.stream.comments():
            self.parse_comment(comment, self.store_comment)


    def parse_comment(self, praw_comment, callback):
        if(praw_comment.author_flair_text != None):
            comment_obj = Comment(praw_comment.id,
                                  praw_comment.author,
                                  praw_comment.created_utc,
                                  praw_comment.author_flair_text,
                                  praw_comment.body)
            if(callback):
                callback(comment_obj)


    def store_comment(self, comment_obj):
        self.db.insert_row( self.static.COMMENTS_COLUMNS,
                            [comment_obj.id.id, comment_obj.author,
                                comment_obj.time, comment_obj.flair, comment_obj.text],
                            self.static.COMMENTS_TABLE,
                            comment_obj.dump)


@click.command()
@click.option("--remote", "-r", is_flag=True,
              help="Denotes whether or not the scraper is accessing the database remotely (using {0} instead of {1})".format(DB_Controller.REMOTE_DB_CFG_NAME, DB_Controller.DB_CFG_NAME))
def main(remote):
    ## Handle the args
    kwargs = {"remote": remote}

    ## Init Scraper
    scraper = Scraper(**kwargs)


if __name__ == '__main__':
    main()
