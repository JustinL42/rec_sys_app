#!/usr/bin/python3
import os, sys
from datetime import datetime
import pandas as pd
import psycopg2

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)

from mysite import settings
from mysite import secret_keys


# On a dry run, print the book found for the title 
# and do everything except actually inserting the data into
DRY_RUN = False

db_name = settings.DATABASES['default'].get('NAME', 'recsysdev')
db_port = settings.DATABASES['default'].get('PORT', '5432')
db_user = settings.DATABASES['default'].get('USER', 'postgres')
db_password = settings.DATABASES['default'].get('PASSWORD', ' ')
db_host = settings.DATABASES['default'].get('HOST', ' ')
db_conn_string = "dbname={} port={} user={} password= {} host={} "\
    .format(db_name, db_port, db_user, db_password, db_host)


conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            username = "isfdb_ratings_virtual"
            first_name = "virtual"
            last_name = "isfdb_ratings"
            password = secret_keys.custom_user_hash
            is_active = False
            is_superuser = False
            is_staff = False
            email = ''
            virtual = True
            if not DRY_RUN:
                cur.execute("""
                    INSERT INTO recsys_user 
                    (username, first_name, last_name, password, 
                        email, is_active, is_superuser, is_staff,
                        date_joined, virtual)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username) 
                    DO UPDATE 
                    SET first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        virtual = EXCLUDED.virtual,
                        date_joined = EXCLUDED.date_joined
                    RETURNING ID;
                """, (username, first_name, last_name, password, 
                        email, is_active, is_superuser, is_staff, 
                        datetime.now(), virtual)
                )
                user_id = cur.fetchone()[0]

                cur.execute("""
                    DELETE
                    FROM recsys_rating
                    WHERE user_id = %s
                """, (user_id,)
                )

            cur.execute("""
                SELECT id, isfdb_rating
                FROM recsys_books
                WHERE isfdb_rating IS NOT NULL
                ORDER BY isfdb_rating;
            """)
            results = cur.fetchall()

            saved = False
            blocked = False
            for title_id, rating in results:
                if not DRY_RUN:
                    cur.execute("""
                        INSERT INTO recsys_rating 
                        (rating, saved, blocked, last_updated, 
                            book_id, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (rating, saved, blocked, datetime.now(), 
                            title_id, user_id)
                    )

except Exception as e:
    raise e
finally:
    conn.close()
