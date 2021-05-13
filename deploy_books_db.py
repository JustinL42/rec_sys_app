#!/usr/bin/env python3

import psycopg2

sql = """
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

    ALTER TABLE old_recsys_isbns 
        RENAME CONSTRAINT live_injective_isbn_to_title_id
        TO old_injective_isbn_to_title_id;

    ALTER TABLE books RENAME TO recsys_books;
    ALTER TABLE isbns RENAME TO recsys_isbns;
    ALTER TABLE translations RENAME TO recsys_translations;
    ALTER TABLE contents RENAME TO recsys_contents;
    ALTER TABLE more_images RENAME TO recsys_more_images;
    ALTER TABLE words RENAME TO recsys_words;

    ALTER TABLE recsys_isbns 
        RENAME CONSTRAINT injective_isbn_to_title_id
        TO live_injective_isbn_to_title_id;


    ALTER TABLE recsys_books RENAME COLUMN title_id to id;
    ALTER TABLE recsys_translations RENAME COLUMN title_id to id;
"""

dest_db_name = "recsyslive"
dest_db_conn_string = "port=5434 dbname={} user=postgres".format(dest_db_name)
dest_conn = psycopg2.connect(dest_db_conn_string)
try:
    with dest_conn:
        with dest_conn.cursor() as dest_cur:
            dest_cur.execute(sql)
finally:
    dest_conn.close()   


