#!/usr/bin/env python3

import psycopg2

dest_db_name = "recsyslive"
dest_db_conn_string = "port=5432 dbname={} user=postgres".format(dest_db_name)


dest_conn = psycopg2.connect(dest_db_conn_string)
try:
    with dest_conn:
        with dest_conn.cursor() as dest_cur:
            dest_cur.execute("""
    DROP TABLE IF EXISTS old_recsys_isbns;
    DROP TABLE IF EXISTS old_recsys_translations;
    DROP TABLE IF EXISTS old_recsys_contents;
    DROP TABLE IF EXISTS old_recsys_more_images;
    DROP TABLE IF EXISTS old_recsys_words;
    DROP TABLE IF EXISTS old_recsys_books;

    ALTER TABLE recsys_books RENAME TO old_recsys_books;
    ALTER TABLE recsys_isbns RENAME TO old_recsys_isbns;
    ALTER TABLE recsys_translations RENAME TO old_recsys_translations;
    ALTER TABLE recsys_contents RENAME TO old_recsys_contents;
    ALTER TABLE recsys_more_images RENAME TO old_recsys_more_images;
    ALTER TABLE recsys_words RENAME TO old_recsys_words;
            """)
finally:
    dest_conn.close()   


dest_conn = psycopg2.connect(dest_db_conn_string)
try:
    with dest_conn:
        with dest_conn.cursor() as dest_cur:
            dest_cur.execute("""
    ALTER TABLE old_recsys_isbns 
        RENAME CONSTRAINT live_injective_isbn_to_title_id
        TO old_injective_isbn_to_title_id;
                """)
except psycopg2.errors.UndefinedObject:
    print("The constraint injective_isbn_to_title_id " + \
        "doesn't exist. Skipping rename")
finally:
    dest_conn.close() 


dest_conn = psycopg2.connect(dest_db_conn_string)
try:
    with dest_conn:
        with dest_conn.cursor() as dest_cur:
            dest_cur.execute("""
    ALTER TABLE books RENAME TO recsys_books;
    ALTER TABLE isbns RENAME TO recsys_isbns;
    ALTER TABLE translations RENAME TO recsys_translations;
    ALTER TABLE contents RENAME TO recsys_contents;
    ALTER TABLE more_images RENAME TO recsys_more_images;
    ALTER TABLE words RENAME TO recsys_words;

    ALTER TABLE recsys_books RENAME COLUMN title_id to id;
    ALTER TABLE recsys_translations RENAME COLUMN title_id to id;
            """)
finally:
    dest_conn.close()  


dest_conn = psycopg2.connect(dest_db_conn_string)
try:
    with dest_conn:
        with dest_conn.cursor() as dest_cur:
            dest_cur.execute("""
    ALTER TABLE recsys_isbns 
        RENAME CONSTRAINT injective_isbn_to_title_id
        TO live_injective_isbn_to_title_id;
                """)
except psycopg2.errors.UndefinedObject:
    print("The constraint injective_isbn_to_title_id " + \
        "doesn't exist. Skipping rename")
finally:
    dest_conn.close() 


# dest_conn = psycopg2.connect(dest_db_conn_string)
# try:
#     with dest_conn:
#         with dest_conn.cursor() as dest_cur:
#             dest_cur.execute(sql1)
#             try:
#                 dest_cur.execute(sql2)
#             except psycopg2.errors.UndefinedObject:
#                 print("The constraint live_injective_isbn_to_title_id " + \
#                     "doesn't exist. Skipping rename")
#             dest_cur.execute(sql3)
#             try:
#                 dest_cur.execute(sql4)
#             except psycopg2.errors.UndefinedObject:
#                 print("The constraint injective_isbn_to_title_id " + \
#                     "doesn't exist. Skipping rename")


# finally:
#     dest_conn.close()   


