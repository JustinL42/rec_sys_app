#!/bin/bash

rm -rf /tmp/recsysold
pg_dump -Fd recsyslive -j 2 -f /tmp/recsysold --verbose -p 5432 -U postgres
pg_restore -d recsysold -j 2 --clean --if-exists --verbose -p 5432 -U postgres /tmp/recsysold

psql -p 5432 -U postgres -d recsyslive -c 'DROP TABLE IF EXISTS recsys_isbns'
psql -p 5432 -U postgres -d recsyslive -c 'DROP TABLE IF EXISTS recsys_translations'
psql -p 5432 -U postgres -d recsyslive -c 'DROP TABLE IF EXISTS recsys_contents'
psql -p 5432 -U postgres -d recsyslive -c 'DROP TABLE IF EXISTS recsys_more_images'
psql -p 5432 -U postgres -d recsyslive -c 'DROP TABLE IF EXISTS recsys_words'
psql -p 5432 -U postgres -d recsyslive -c 'DROP TABLE IF EXISTS recsys_books'


rm -rf /tmp/recsyslive
pg_dump -Fd recsysetl -j 2 -f /tmp/recsyslive --verbose -p 5432 -U postgres
pg_restore -d recsyslive -j 2 --clean --if-exists --verbose -p 5432 -U postgres /tmp/recsyslive


psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE books RENAME TO recsys_books'
psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE isbns RENAME TO recsys_isbns'
psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE translations RENAME TO recsys_translations'
psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE contents RENAME TO recsys_contents'
psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE more_images RENAME TO recsys_more_images'
psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE words RENAME TO recsys_words'

psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE recsys_books RENAME COLUMN title_id to id'
psql -p 5432 -U postgres -d recsyslive -c 'ALTER TABLE recsys_translations RENAME COLUMN title_id to id'