#!/usr/bin/python3
import os
import pandas as pd
import psycopg2

from mysite import settings
from mysite import secret_keys

db_name = settings.DATABASES['default'].get('NAME', 'recsysdev')
db_port = settings.DATABASES['default'].get('PORT', '5432')
db_user = settings.DATABASES['default'].get('USER', 'postgres')
db_password = settings.DATABASES['default'].get('PASSWORD', ' ')
db_host = settings.DATABASES['default'].get('HOST', ' ')
db_conn_string = "dbname={} port={} user={} password= {} host={} "\
    .format(db_name, db_port, db_user, db_password, db_host)

data_dir = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(data_dir,
    "custom/ratings by book title and user 2021-03-16.csv")
name_key_file = os.path.join(data_dir,
    "custom/name_key.csv")
df = pd.read_csv(filename)

#remove a known incorrect rating
df.drop(index=406, inplace=True)

#remove null ratings
df = df[~df.Value.isnull()]

# For duplicates on name, title, and rating, keep only the first one
df = df[~df.duplicated(subset=['Name', 'Title', 'Value'], keep='first')]

# Fix some inconsistent naming
df.loc[(df.Name =="Mike") | (df.Name == "Michael"), 'Name'] = "Mike N."


# Before 1/21/2020, ratings were recorded from -1 to 1
# After, they were 1-5
# convert these to 1-10
df['original_rating'] = df['Value']
df.Timestamp = pd.to_datetime(df.Timestamp)
conversion = lambda r : max(1, min(10, (r * 3) + 5.5))
df.loc[df.Timestamp < '1/21/20', 'Value'] = df['Value'].map(conversion)
conversion = lambda r : max(1, min(10, r * 2))
df.loc[df.Timestamp >= '1/21/20', 'Value'] = df['Value'].map(conversion)


df['original_min'] = -1
df['original_max'] = 1
df.loc[df.Timestamp >= '1/21/20', 'original_min'] = 1
df.loc[df.Timestamp >= '1/21/20', 'original_max'] = 5


if os.path.exists(name_key_file):
    name_key = pd.read_csv(name_key_file)
else:
    name_series = df.Name.drop_duplicates()
    name_series.reset_index(drop=True, inplace=True)
    numeric_alias = pd.Series(
        range(5001, 5001 + name_series.shape[0]), name="Numeric Alias")
    name_key = pd.concat([name_series, numeric_alias], axis=1)

name_key_dict = dict(name_key[['Name', 'Numeric Alias']].values)


conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:
            title_series = df.Title.drop_duplicates()
            for title in title_series:
                title = title.lower().strip()
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
                    """, (title, title, title))
                results = cur.fetchall()
                if results:
                    print(results[0])
                else:
                    print("No results for {}".format(title))

except Exception as e:
    raise e
finally:
    conn.close()




