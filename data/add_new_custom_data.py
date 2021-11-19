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
CUSTOM_BOOK_CLUB_ID = 8
filename = "custom/ratings_2021-11-18.tsv"
name_key_file = "custom/name_key.csv"
opt_out_list_file = "custom/opt_out_list.txt"

data_dir = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(data_dir, filename)
name_key_file = os.path.join(data_dir, name_key_file)
opt_out_list_file = os.path.join(data_dir, opt_out_list_file)
df = pd.read_csv(filename, sep="\t")

db_name = settings.DATABASES['default'].get('NAME', 'recsysdev')
db_port = settings.DATABASES['default'].get('PORT', '5432')
db_user = settings.DATABASES['default'].get('USER', 'postgres')
db_password = settings.DATABASES['default'].get('PASSWORD', ' ')
db_host = settings.DATABASES['default'].get('HOST', ' ')
db_conn_string = "dbname={} port={} user={} password= {} host={} "\
    .format(db_name, db_port, db_user, db_password, db_host)

def convert_to_1_to_10(data):
    rating = data.rating
    min_rating = data.min_rating
    max_rating = data.max_rating
    if ((max_rating - min_rating) > (10 - 1)):
        return (rating - min_rating) * (10 - 1) / \
            (max_rating - min_rating) + 1
    else:
        max_from_one = max_rating - (min_rating - 1)
        rating_from_one = rating - (min_rating - 1)
        shift_to_center = (1 - (10 / max_from_one)) / 2
        return rating_from_one * 10 / max_from_one + shift_to_center

df = df[~df.rating.isnull()]
df['original_rating'] = df.rating
df.rating = df.apply(convert_to_1_to_10, axis=1)
df.date = pd.to_datetime(df.date)


name_key = pd.read_csv(name_key_file)
last_alias = int(max(
    name_key[ name_key['Numeric Alias'] < 'A' ]['Numeric Alias']))
member_dict = dict([(x[1]['Name'].lower(), x[1]['Numeric Alias']) \
    for x in name_key.iterrows()])
name_series = df.name.drop_duplicates()

if os.path.exists(opt_out_list_file):
    with open(opt_out_list_file) as file:
        opt_out_set = set([row.strip().lower() \
            for row in file.readlines()])
else:
    opt_out_set = set()

title_series = df.title.drop_duplicates()
title_dict = {}

meetings_df = df[['title', 'date']]
meetings_df = meetings_df[~meetings_df.duplicated(keep='first')]

conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            # Getting title IDs
            for title in title_series:
                title_lower = title.lower().strip()
                cur.execute("""
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
                    """, (title_lower, title_lower, title_lower))
                results = cur.fetchall()
                if results:
                    if DRY_RUN:
                        print(results[0])
                    title_dict[title] = results[0][0]
                else:
                    print('No results for "{}"'.format(title))

            last_name = ""
            password = secret_keys.custom_user_hash
            is_active = False
            is_superuser = False
            is_staff = False
            date_joined = datetime.now()
            email = ''
            virtual = False

            #Add any new members to user and book club member tables
            for name in name_series:
                name_lower = name.lower()
                if name_lower in member_dict or name_lower in opt_out_set:
                    continue
                last_alias += 1
                member_dict[name_lower] = username = str(last_alias)
                if not DRY_RUN:
                    cur.execute("""
                        INSERT INTO recsys_user 
                        (username, first_name, last_name, password, 
                            email, is_active, is_superuser,
                            is_staff, date_joined, virtual)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username)
                        DO UPDATE
                            -- Needed to get the id returned
                            SET username = EXCLUDED.username
                        RETURNING id;
                    """, (username, username, last_name, password, 
                            email, is_active, is_superuser,
                            is_staff, date_joined, virtual)
                    )
                    member_id = cur.fetchone()[0]

                    cur.execute("""
                        INSERT INTO recsys_book_club_members
                        (book_club_id, user_id)
                        VALUES (%s, %s)
                        ON CONFLICT (book_club_id, user_id)
                        DO NOTHING;
                    """, (CUSTOM_BOOK_CLUB_ID, member_id)
                    )

                    print("\n{},{}".format(name, username), 
                        file=open(name_key_file, "a"), end="")
                else:
                    print("Add to name_key: {},{}".format(name, username))

            #Add meetings for each book in the list.
            #For idempotency, delete any old entry first.
            for index, row in meetings_df.iterrows():
                book_id = title_dict[row.title]
                if not DRY_RUN:
                    cur.execute("""
                        DELETE 
                        FROM recsys_meeting
                        WHERE book_id = %s
                        AND book_club_id = %s;
                    """, (book_id, CUSTOM_BOOK_CLUB_ID))

                    cur.execute("""
                        INSERT INTO recsys_meeting
                        (date, book_id, book_club_id)
                        VALUES (%s, %s, %s)
                    """, (row.date, book_id, CUSTOM_BOOK_CLUB_ID))

            # Add or update the ratings
            saved = False
            blocked = False
            for index, row in df.iterrows():
                book_id = title_dict[row.title]
                username = member_dict[row['name'].lower()]
    
                if not DRY_RUN:
                    cur.execute("""
                        INSERT INTO recsys_rating 
                        (original_rating, original_min, original_max, 
                            original_book_id, rating, saved, blocked, 
                            last_updated, book_id, user_id)
                        SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, u.id
                        FROM recsys_user as u
                        WHERE u.username = %s
                        ON CONFLICT (book_id, user_id)
                        DO UPDATE
                            SET rating = EXCLUDED.rating,
                            original_rating = EXCLUDED.original_rating,
                            original_min = EXCLUDED.original_min,
                            original_max = EXCLUDED.original_max,
                            original_book_id = EXCLUDED.original_book_id,
                            last_updated = EXCLUDED.last_updated

                    """, (row.original_rating, row.min_rating, 
                            row.max_rating, row.title, row.rating, saved, 
                            blocked, row.date, book_id, username)
                    )

except Exception as e:
    raise e
