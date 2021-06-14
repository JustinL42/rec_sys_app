#!/bin/bash

rm -rf /tmp/recsysold
/usr/lib/postgresql/13/bin/pg_dump -Fd recsysdev -j 3 -f /tmp/recsysold --verbose -p 5434 -U postgres
/usr/lib/postgresql/13/bin/pg_restore -d recsysold -j 3 --clean --if-exists --verbose -p 5434 -U postgres /tmp/recsysold 

psql -p 5434 -U postgres -d recsysdev -c 'DROP TABLE IF EXISTS recsys_isbns'
psql -p 5434 -U postgres -d recsysdev -c 'DROP TABLE IF EXISTS recsys_translations'
psql -p 5434 -U postgres -d recsysdev -c 'DROP TABLE IF EXISTS recsys_contents'
psql -p 5434 -U postgres -d recsysdev -c 'DROP TABLE IF EXISTS recsys_more_images'
psql -p 5434 -U postgres -d recsysdev -c 'DROP TABLE IF EXISTS recsys_words'
psql -p 5434 -U postgres -d recsysdev -c 'DROP TABLE IF EXISTS recsys_books'


rm -rf /tmp/recsysdev
/usr/lib/postgresql/13/bin/pg_dump -Fd recsysetl -j 3 -f /tmp/recsysdev --verbose -p 5434 -U postgres
/usr/lib/postgresql/13/bin/pg_restore -d recsysdev -j 3 --clean --if-exists --verbose -p 5434 -U postgres /tmp/recsysdev
psql -p 5434 -U postgres -d recsysdev -c 'CREATE EXTENSION IF NOT EXISTS fuzzystrmatch'
psql -p 5434 -U postgres -d recsysdev -c 'CREATE EXTENSION IF NOT EXISTS unaccent'
psql -p 5434 -U postgres -d recsysdev -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm'



psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE books RENAME TO recsys_books'
psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE isbns RENAME TO recsys_isbns'
psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE translations RENAME TO recsys_translations'
psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE contents RENAME TO recsys_contents'
psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE more_images RENAME TO recsys_more_images'
psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE words RENAME TO recsys_words'

psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE recsys_books RENAME COLUMN title_id to id'
psql -p 5434 -U postgres -d recsysdev -c 'ALTER TABLE recsys_translations RENAME COLUMN title_id to id'
psql -p 5434 -U postgres -d recsysdev -c 'ANALYZE'

psql -p 5434 -U postgres -d recsysdev -c 'SELECT book_id FROM recsys_rating WHERE NOT EXISTS (SELECT 1 FROM recsys_books WHERE id = recsys_rating.book_id);'
# psql -p 5434 -U postgres -d recsysdev -c 'DELETE FROM recsys_rating WHERE NOT EXISTS (SELECT 1 FROM recsys_books WHERE id = recsys_rating.book_id);'
