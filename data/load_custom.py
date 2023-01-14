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
BOOK_CLUB_NAME = "Custom Book Club"

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
filename = os.path.join(
    data_dir, "custom/ratings by book title and user 2021-03-16.csv"
)
name_key_file = os.path.join(data_dir, "custom/name_key.csv")
opt_out_list_file = os.path.join(data_dir, "custom/opt_out_list.txt")
df = pd.read_csv(filename)

# remove a known incorrect rating
df.drop(index=406, inplace=True)

# remove null ratings
df = df[~df.Value.isnull()]

# For duplicates on name, title, and rating, keep only the first one
df = df[~df.duplicated(subset=["Name", "Title", "Value"], keep="first")]

# Fix some inconsistent naming
df.loc[(df.Name == "Mike") | (df.Name == "Michael"), "Name"] = "Mike N."


# Before 1/21/2020, ratings were recorded from -1 to 1
# After, they were 1-5
# convert these to 1-10
df["original_rating"] = df["Value"]
df.Timestamp = pd.to_datetime(df.Timestamp)
df.loc[df.Timestamp < "1/21/20", "Value"] = df["Value"].map(
    lambda r: max(1, min(10, (r * 3.5) + 5.5))
)
df.loc[df.Timestamp >= "1/21/20", "Value"] = df["Value"].map(
    lambda r: max(1, min(10, r * 2 - 0.5))
)


df["original_min"] = -1
df["original_max"] = 1
df.loc[df.Timestamp >= "1/21/20", "original_min"] = 1
df.loc[df.Timestamp >= "1/21/20", "original_max"] = 5


if os.path.exists(name_key_file):
    name_key = pd.read_csv(name_key_file)
else:
    name_series = df.Name.drop_duplicates()
    name_series.reset_index(drop=True, inplace=True)
    numeric_alias = pd.Series(
        range(5001, 5001 + name_series.shape[0]), name="Numeric Alias"
    )
    name_key = pd.concat([name_series, numeric_alias], axis=1)
    name_key.to_csv(name_key_file)

if os.path.exists(opt_out_list_file):
    with open(opt_out_list_file) as file:
        opt_out_set = set([row.strip() for row in file.readlines()])
else:
    opt_out_set = set()

title_series = df.Title.drop_duplicates()
title_dict = {}

meetings_df = df[["Title", "Timestamp"]]
meetings_df = meetings_df[~meetings_df.duplicated(keep="first")]

conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            for title in title_series:
                title_lower = title.lower().strip()
                cur.execute(
                    """
                    SELECT id, title, year, authors
                    FROM recsys_books
                    WHERE general_search @@
                        websearch_to_tsquery('isfdb_title_tsc', %s )
                    ORDER BY
                        CASE
                            WHEN (LOWER(title) = %s) THEN 1
                            ELSE 2
                        END ASC,
                        editions DESC,
                        ts_rank_cd(general_search,
                            websearch_to_tsquery('isfdb_title_tsc', %s
                        ), 8) DESC,
                        id ASC;
                    """,
                    (title_lower, title_lower, title_lower),
                )
                results = cur.fetchall()
                if results:
                    if DRY_RUN:
                        print(results[0])
                    title_dict[title] = results[0][0]
                else:
                    print(f'No results for "{title}"')

            print("Loading user data...")
            last_name = ""
            password = config["custom_user_hash"]
            is_active = False
            is_superuser = False
            is_staff = False
            date_joined = datetime.now()
            email = ""
            virtual = False

            member_ids = []
            member_dict = {}
            for index, row in name_key.iterrows():

                name = row["Name"]
                if name in opt_out_set:
                    continue

                username = row["Numeric Alias"]
                first_name = row["Numeric Alias"]

                if not DRY_RUN:
                    cur.execute(
                        """
                        INSERT INTO recsys_user
                        (username, first_name, last_name, password, email,
                            is_active, is_superuser,
                            is_staff, date_joined, virtual)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username)
                        DO UPDATE
                            SET first_name = EXCLUDED.first_name
                        RETURNING id;
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
                            date_joined,
                            virtual,
                        ),
                    )
                    member_id = cur.fetchone()[0]
                else:
                    member_id = index
                member_ids.append(member_id)
                member_dict[name] = member_id

            if not DRY_RUN:
                # Create the virtual user, whose ratings are the
                # average for the book crossings users as a whole
                username = BOOK_CLUB_NAME + "_virtual"
                first_name = "virtual"
                virtual = True
                cur.execute(
                    """
                    INSERT INTO recsys_user
                    (username, first_name, last_name, password, email,
                        is_active, is_superuser, is_staff,
                        date_joined, virtual)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username)
                    DO UPDATE
                    SET first_name = EXCLUDED.first_name,
                        virtual = EXCLUDED.virtual
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
                        date_joined,
                        virtual,
                    ),
                )
                virtual_user_id = cur.fetchone()[0]

                # delete any prior virtual book club
                cur.execute(
                    """
                    SELECT id
                    FROM recsys_book_club
                    WHERE name = %s;
                """,
                    (BOOK_CLUB_NAME,),
                )
                existing_custom_clubs = cur.fetchall()
                for club in existing_custom_clubs:
                    cur.execute(
                        """
                        DELETE
                        FROM recsys_book_club_members
                        WHERE book_club_id = %s
                        """,
                        club,
                    )
                    cur.execute(
                        """
                        DELETE
                        FROM recsys_meeting
                        WHERE book_club_id = %s
                        """,
                        club,
                    )
                cur.execute(
                    """
                    DELETE
                    FROM recsys_book_club
                    WHERE name = %s;
                    """,
                    (BOOK_CLUB_NAME,),
                )

                # create the virtual book club
                cur.execute(
                    """
                    INSERT INTO recsys_book_club
                    (name, virtual, virtual_member_id)
                    VALUES (%s, %s, %s)
                    RETURNING ID;
                """,
                    (BOOK_CLUB_NAME, True, virtual_user_id),
                )

                # populate the virtual book club
                virtual_book_club_id = cur.fetchone()[0]
                for member_id in member_ids:
                    cur.execute(
                        """
                        INSERT INTO recsys_book_club_members
                        (book_club_id, user_id)
                        VALUES (%s, %s)
                    """,
                        (virtual_book_club_id, member_id),
                    )

                    # delete any pre-existing ratings for these users
                    cur.execute(
                        """
                        DELETE
                        FROM recsys_rating
                        where user_id = %s
                    """,
                        (member_id,),
                    )

                # TODO: update the virtual user's ratings
                # update_virtual_user("BookCrossing")

            for index, row in meetings_df.iterrows():
                date = row.Timestamp
                try:
                    book_id = title_dict[row.Title]
                except KeyError:
                    pass
                if not DRY_RUN:
                    cur.execute(
                        """
                        INSERT INTO recsys_meeting
                        (date, book_id, book_club_id)
                        VALUES (%s, %s, %s)
                    """,
                        (date, book_id, virtual_book_club_id),
                    )

            print("Loading ratings data...")

            saved = False
            blocked = False
            for index, row in df.iterrows():
                try:
                    book_id = title_dict[row.Title]
                    user_id = member_dict[row.Name]
                except KeyError:
                    continue
                original_min = row.original_min
                original_max = row.original_max
                original_rating = max(
                    original_min, min(original_max, row.original_rating)
                )
                rating = row.Value
                last_updated = row.Timestamp

                if not DRY_RUN:
                    cur.execute(
                        """
                        INSERT INTO recsys_rating
                        (original_rating, original_min, original_max,
                            original_book_id, rating, saved, blocked,
                            last_updated, book_id, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                        (
                            original_rating,
                            original_min,
                            original_max,
                            row.Title,
                            rating,
                            saved,
                            blocked,
                            last_updated,
                            book_id,
                            user_id,
                        ),
                    )

except Exception as e:
    raise e
finally:
    conn.close()
