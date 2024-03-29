#!/usr/bin/python3
import configparser
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(BASE_DIR)


# On a dry run, print the book found for the title
# and do everything except actually inserting the data into
DRY_RUN = False
OVERWRITE_EXISTING = True
FILE = "goodreads/j_goodreads_library_export.csv"
USERNAME = "5013"
INCONSISTENT_ISBN_VIRTUAL_TITLE = 73
ORIGINAL_MIN = 1
ORIGINAL_MAX = 5

# Get per-environment settings from the config files.
CONFIG_DIR = Path(BASE_DIR, "config")
CONFIG_FILES = [Path(CONFIG_DIR, f) for f in os.listdir(CONFIG_DIR)]
ENV = os.environ.get("ENV", "DEFAULT")
config_parser = configparser.ConfigParser()
config_parser.read(CONFIG_FILES)
config = config_parser[ENV]

db_conn_string = (
    f"dbname={config['db_name']} port={config['db_port']} "
    + f"user={config['db_user']} password= {config['db_password']} "
    + f"host={config['db_host']} "
)

data_dir = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(data_dir, FILE)


def conversion(rating):
    return max(1, min(10, rating * 2 - 0.5))


gr_df = pd.read_csv(filename, sep=",", quotechar='"')
gr_df = gr_df[gr_df["My Rating"] != 0]


ratings_dict = {}
inconsistent_isbns = set()
conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT ID
                FROM recsys_user
                WHERE username = %s;
                """,
                (USERNAME,),
            )
            user_id = cur.fetchone()[0]
            if not user_id:
                raise Exception(f"No user for username: {USERNAME}")

            for i, row in gr_df.iterrows():

                isbn = row.ISBN13.split('"')[1]
                if not isbn:
                    isbn = row.ISBN.split('"')[1]
                if not isbn:
                    continue

                cur.execute(
                    """
                    select title_id
                    from recsys_isbns
                    where isbn  = %s;
                    """,
                    (isbn,),
                )
                book_id = cur.fetchone()
                if not book_id:
                    continue
                if book_id[0] == INCONSISTENT_ISBN_VIRTUAL_TITLE:
                    inconsistent_isbns.add(isbn)
                    continue

                rating_list, isbns_set = ratings_dict.get(
                    book_id[0], ([], set())
                )
                rating_list.append(float(row["My Rating"]))
                isbns_set.add(isbn)
                ratings_dict[book_id[0]] = (rating_list, isbns_set)

            saved = False
            blocked = False
            last_updated = datetime.now()
            for book_id, (rating_list, isbns_set) in ratings_dict.items():
                rating = sum(rating_list) / len(rating_list)
                original_book_id = ", ".join(sorted(isbns_set))

                if not DRY_RUN:
                    if OVERWRITE_EXISTING:
                        cur.execute(
                            """
                            INSERT INTO recsys_rating
                            (rating, saved, blocked, last_updated,
                                book_id, user_id, original_book_id,
                                original_rating, original_min, original_max)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (book_id, user_id) DO UPDATE SET
                                rating = EXCLUDED.rating,
                                last_updated = EXCLUDED.last_updated,
                                original_book_id = EXCLUDED.original_book_id;
                        """,
                            (
                                conversion(rating),
                                saved,
                                blocked,
                                last_updated,
                                book_id,
                                user_id,
                                original_book_id,
                                rating,
                                ORIGINAL_MIN,
                                ORIGINAL_MAX,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO recsys_rating
                            (rating, saved, blocked, last_updated,
                                book_id, user_id, original_book_id,
                                original_rating, original_min, original_max)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING;
                        """,
                            (
                                conversion(rating),
                                saved,
                                blocked,
                                last_updated,
                                book_id,
                                user_id,
                                original_book_id,
                                rating,
                                ORIGINAL_MIN,
                                ORIGINAL_MAX,
                            ),
                        )

except Exception as e:
    raise e
finally:
    conn.close()

if inconsistent_isbns:
    print("Inconsistent ISBNs were skipped:")
for isbn in inconsistent_isbns:
    print(isbn)
