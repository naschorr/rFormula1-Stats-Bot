from __future__ import print_function

import sys
import click

from db_controller import DB_Controller
from comment import Comment
from exception_helper import ExceptionHelper


class DB_Comment_Frequency:
    ## Literals
    MAIN_DB_TABLE = "comments"
    HOURLY_DB_TABLE = "hourly_flair_frequency"
    HOURLY_COLUMNS = ["flair", "frequency", "time_of"]
    APPEND_ARG = "append"

    ## Precomputes the hourly flair frequency of the comments, and stores them
    ## into a new table created with:
    """
    CREATE TABLE hourly_flair_frequency (
        id serial PRIMARY KEY,
        flair text NOT NULL,
        frequency integer NOT NULL,
        time_of integer NOT NULL
    );
    """

    def __init__(self, **kwargs):
        self.static = DB_Comment_Frequency

        ## Init the exception helper
        self.exception_helper = ExceptionHelper(log_time=True, std_stream=sys.stderr)

        ## Init the DB
        kwargs["suppress_greeting"] = True
        self.db_controller = DB_Controller(**kwargs)
        self.db = self.db_controller.db

        ## Check and see if this should be ran in append mode -- adjust start accordinly
        if(kwargs.get(self.static.APPEND_ARG, False)):
            start = self.get_last_frequency_time()
        else:
            start = self.get_first_time_created()

        ## Reconfigure for different time steps
        ## Start getting hour data and inserting into the table
        hour_generator = self.generate_hourly_seconds_range(start,
                                                            self.get_last_time_created())
        previous = next(hour_generator)
        for current in hour_generator:
            flair_frequencies = self.get_flair_frequency_between_epoch(previous, current)
            self.store_flair_frequencies(previous, flair_frequencies)
            previous = current


    def get_first_time_created(self, table=None):
        if(not table):
            table = self.static.MAIN_DB_TABLE

        with self.db.cursor() as cursor:
            raw = """SELECT time_created FROM {0}
                     ORDER BY time_created ASC LIMIT 1;"""

            try:
                cursor.execute(raw.format(table))
            except Exception as e:
                self.exception_helper.print(e, "Unexpected error when getting most recent time_created row from the database.\n", exit=True)
            else:
                return cursor.fetchone()[0]


    def get_last_time_created(self, table=None):
        if(not table):
            table = self.static.MAIN_DB_TABLE

        with self.db.cursor() as cursor:
            raw = """SELECT time_created FROM {0}
                     ORDER BY time_created DESC LIMIT 1;"""

            try:
                cursor.execute(raw.format(table))
            except Exception as e:
                self.exception_helper.print(e, "Unexpected error when getting most recent time_created row from the database.\n", exit=True)
            else:
                return cursor.fetchone()[0]


    def get_last_frequency_time(self, table=None):
        if(not table):
            table = self.static.HOURLY_DB_TABLE

        with self.db.cursor() as cursor:
            raw = """SELECT time_of FROM {0}
                     ORDER BY time_of DESC LIMIT 1;"""

            try:
                cursor.execute(raw.format(table))
            except Exception as e:
                self.exception_helper.print(e, "Unexpected error when getting most recent time_created row from the database.\n", exit=True)
            else:

                try:
                    return cursor.fetchone()[0]
                except TypeError as e:
                    self.exception_helper.print(e, "TypeError when getting most recent time_of row from the database. Try without 'append' mode.\n", exit=True)
                except Exception as e:
                    self.exception_helper.print(e, "Unexpected error when getting most recent time_of row from the database.\n", exit=True)



    def generate_hourly_seconds_range(self, start, end):
        ## Get start of next complete hour
        start_mod = start % 3600
        start = start - start_mod + (3600 if start_mod > 0 else 0)

        for index in range(start, end + 1, 3600):
            yield index


    def get_flair_frequency_between_epoch(self, start, end, table=None):
        if(not table):
            table = self.static.MAIN_DB_TABLE

        with self.db.cursor() as cursor:
            raw = """SELECT flair, count(flair) as frequency FROM {0}
                     WHERE time_created BETWEEN %s AND %s
                     GROUP BY flair
                     ORDER BY COUNT(flair) DESC;"""

            try:
                cursor.execute(raw.format(table), (start, end))
            except Exception as e:
                self.exception_helper.print(e, "Unexpected error when loading comments from between two epochs.\n", exit=True)
            else:
                return cursor.fetchall()


    def store_flair_frequencies(self, start_epoch, flair_frequencies, table=None):
        if(not table):
            table = self.static.HOURLY_DB_TABLE

        self.db.insert_row(self.static.HOURLY_COLUMNS, 
                           [flair_frequency[0], flair_frequency[1], start_epoch], 
                           self.static.HOURLY_DB_TABLE)


@click.command()
@click.option("--remote", "-r", is_flag=True,
              help="Denotes whether or not the comment frequency mover is accessing the database remotely (using {0} instead of {1})".format(DB_Controller.REMOTE_DB_CFG_NAME, DB_Controller.DB_CFG_NAME))
@click.option("--append", "-a", is_flag=True, help="Choose to only append the most recent comments into the flair frequency table, rather than the whole comments table.")
def main(remote, append):
    kwargs = {"remote": remote, DB_Comment_Frequency.APPEND_ARG: append}

    DB_Comment_Frequency(**kwargs)


if __name__ == "__main__":
    main()
