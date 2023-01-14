#!/usr/bin/python3
import configparser
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(BASE_DIR)

# On a dry run, print the book found for the title
# and do everything except actually inserting the data into
DRY_RUN = False

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


conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            username = "isfdb_ratings_virtual"
            first_name = "virtual"
            last_name = "isfdb_ratings"
            password = config["custom_user_hash"]
            is_active = False
            is_superuser = False
            is_staff = False
            email = ""
            virtual = True
            if not DRY_RUN:
                cur.execute(
                    """
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
                """,
                    (
                        username,
                        first_name,
                        last_name,
                        password,
                        email,
                        is_active,
                        is_superuser,
                        is_staff,
                        datetime.now(),
                        virtual,
                    ),
                )
                user_id = cur.fetchone()[0]

                cur.execute(
                    """
                    DELETE
                    FROM recsys_rating
                    WHERE user_id = %s
                """,
                    (user_id,),
                )

            cur.execute(
                """
                SELECT id, isfdb_rating
                FROM recsys_books
                WHERE isfdb_rating IS NOT NULL
                ORDER BY isfdb_rating;
            """
            )
            results = cur.fetchall()

            saved = False
            blocked = False
            for title_id, rating in results:
                if not DRY_RUN:
                    cur.execute(
                        """
                        INSERT INTO recsys_rating
                        (rating, saved, blocked, last_updated,
                            book_id, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                        (
                            rating,
                            saved,
                            blocked,
                            datetime.now(),
                            title_id,
                            user_id,
                        ),
                    )

except Exception as e:
    raise e
finally:
    conn.close()
