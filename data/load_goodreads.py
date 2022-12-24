#!/usr/bin/python3
import os
import sys
from datetime import datetime

import pandas as pd
import psycopg2

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)

from mysite import secret_keys, settings

# On a dry run, print the book found for the title
# and do everything except actually inserting the data into
DRY_RUN = False
OVERWRITE_EXISTING = True
FILE = "goodreads/j_goodreads_library_export.csv"
USERNAME = "5013"
INCONSISTENT_ISBN_VIRTUAL_TITLE = 73
ORIGINAL_MIN = 1
ORIGINAL_MAX = 5
conversion = lambda r: max(1, min(10, r * 2 - 0.5))

db_name = settings.DATABASES["default"].get("NAME", "recsysdev")
db_port = settings.DATABASES["default"].get("PORT", "5432")
db_user = settings.DATABASES["default"].get("USER", "postgres")
db_password = settings.DATABASES["default"].get("PASSWORD", " ")
db_host = settings.DATABASES["default"].get("HOST", " ")
db_conn_string = "dbname={} port={} user={} password= {} host={} ".format(
    db_name, db_port, db_user, db_password, db_host
)

data_dir = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(data_dir, FILE)

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
                raise Exception("No user for username: {}".format(USERNAME))

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
                elif book_id[0] == INCONSISTENT_ISBN_VIRTUAL_TITLE:
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
