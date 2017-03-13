from __future__ import print_function

import json
import sys
import os

if(os.name == "posix"):
    ## https://mail.python.org/pipermail/pypy-dev/2013-May/011398.html
    import psycopg2cffi as psycopg2
elif(os.name == "nt"):
    import psycopg2
else:
    ## No idea what os it is, just try psycopg2
    import psycopg2

from exception_helper import Exception_Helper


class DB_Controller:
    def __init__(self, db_cfg_path):
        ## Init the exception helper
        self.exception_helper = Exception_Helper(log_time=True, std_stream=sys.stderr)

        ## Get config data for the database
        with open(db_cfg_path) as db_json:
            self.db_cfg = json.load(db_json)

        ## Open a connection to the database
        try:
            self.db = psycopg2.connect(database=self.db_cfg["database"],
                                       host=self.db_cfg["hostname"],
                                       user=self.db_cfg["username"],
                                       password=self.db_cfg["password"])
        except psycopg2.OperationalError as e:
            self.exception_helper.print(e, "Unable to connect to the database.\n", exit=True)
        except Exception as e:
            self.exception_helper.print(e, "Unexpected error when trying to connect to the database.\n", exit=True)

        ## Get the table that'll be worked with
        self.table = self.db_cfg["table"]

        ## Display row count on startup
        print("Currently {0} rows in table {1}.".format(self.count_rows(), self.table))


    def count_rows(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM {0};".format(self.table))
            return cursor.fetchone()[0]


    def store_comment(self, comment_obj):
        ## Stage changes to the db
        with self.db.cursor() as cursor:
            raw =  """INSERT INTO {0} (post_id, author, time_created, flair, 
                      body) VALUES (%s, %s, %s, %s, %s);"""
            try:
                cursor.execute(raw.format(self.table), (comment_obj.id.id,
                                                        comment_obj.author,
                                                        comment_obj.time,
                                                        comment_obj.flair,
                                                        comment_obj.text))
            except psycopg2.IntegrityError as e:
                self.exception_helper.print(e, "Primary key integrity error.\n")
                self.db.rollback()
            except Exception as e:
                self.exception_helper.print(e, "Unexpected error when storing comment into the database.\n", exit=True)
            else:

                ## Commit changes to the db
                try:
                    self.db.commit()
                except Exception as e:
                    self.exception_helper.print(e, "Unexpected error when committing changes to the database.\n", exit=True)
                else:

                    ## Output the successfully added comment
                    self.dump_comment(comment_obj)


    def dump_comment(self, comment_obj):
        try:
            comment_obj.print_all()
            sys.stdout.flush()
        except UnicodeEncodeError as e:
            self.exception_helper.print(e, "Error rendering this comment's unicode. Skipping...\n")