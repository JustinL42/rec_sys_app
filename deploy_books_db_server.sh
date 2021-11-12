#!/bin/bash

echo dumping recsyslive to /tmp/recsysold...
rm -rf /tmp/recsysold
pg_dump -Fd recsyslive -j 2 -f /tmp/recsysold -p 5432 -U postgres
echo restoring /tmp/recsysold to recsysold db...
pg_restore -d recsysold -j 2 --create --clean --if-exists -p 5432 -U postgres /tmp/recsysold

echo Dropping recsyslive tables...
psql -p 5432 -U postgres -d recsyslive -c "
DROP TABLE IF EXISTS recsys_isbns
DROP TABLE IF EXISTS recsys_translations
DROP TABLE IF EXISTS recsys_contents
DROP TABLE IF EXISTS recsys_more_images
DROP TABLE IF EXISTS recsys_words
DROP TABLE IF EXISTS recsys_books"

echo dumping recsysetl to /tmp/recsyslive...
rm -rf /tmp/recsyslive
pg_dump -Fd recsysetl -j 2 -f /tmp/recsyslive -p 5432 -U postgres
echo restoring /tmp/recsyslive to recsyslive db...
pg_restore -d recsyslive -j 2 --clean --if-exists -p 5432 -U postgres /tmp/recsyslive

echo creating db extensions...
psql -p 5432 -U postgres -d recsyslive -c "
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch
CREATE EXTENSION IF NOT EXISTS unaccent
CREATE EXTENSION IF NOT EXISTS pg_trgm"

psql -p 5432 -U postgres -d recsyslive -c "
ALTER TABLE books RENAME TO recsys_books
ALTER TABLE isbns RENAME TO recsys_isbns
ALTER TABLE translations RENAME TO recsys_translations
ALTER TABLE contents RENAME TO recsys_contents
ALTER TABLE more_images RENAME TO recsys_more_images
ALTER TABLE words RENAME TO recsys_words
ALTER TABLE recsys_books RENAME COLUMN title_id to id
ALTER TABLE recsys_translations RENAME COLUMN title_id to id

SELECT distinct book_id FROM recsys_rating WHERE NOT EXISTS (SELECT 1 FROM recsys_books WHERE id = recsys_rating.book_id);"

# psql -p 5432 -U postgres -d recsyslive -c 'DELETE FROM recsys_rating WHERE NOT EXISTS (SELECT 1 FROM recsys_books WHERE id = recsys_rating.book_id);'
