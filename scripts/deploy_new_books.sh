#!/bin/bash

# SETTINGS

DB_PORT=5432
DB_USER=postgres

# Number of jobs to use. Default is all but one.
N_JOBS=$(nproc --ignore=1)

# Update these hostnames to the ones used on your environments:
DEV_HOSTNAME=t420s
LIVE_HOSTNAME=nuc

# Determine the application db name.
DEV_DB_NAME=recsysdev
LIVE_DB_NAME=recsyslive
case $(hostname) in
	$DEV_HOSTNAME)
		APP_DB=$DEV_DB_NAME
		;;
	$LIVE_HOSTNAME)
		APP_DB=$LIVE_DB_NAME
		;;
	*)
		echo -e "\nHostname not recognized."
		echo -e "Did you set the *_HOSTNAME variables in the script?"
		echo DEPLOY FAILED
		;;
esac

echo -e "\nDumping $APP_DB db to /tmp/recsysold..."
rm -rf /tmp/recsysold 2> /dev/null
pg_dump \
	$APP_DB \
	--file=/tmp/recsysold \
	--format=directory \
	--jobs=$N_JOBS \
	--port=$DB_PORT \
	--username=$DB_USER \
	|| { echo DEPLOY FAILED; exit 1;}

echo -e "\nBacking up /tmp/recsysold to recsysold db..."
dropdb recsysold --if-exists --username=$DB_USER
createdb recsysold --template=$APP_DB --username=$DB_USER
pg_restore \
	/tmp/recsysold \
	--dbname=recsysold \
	--clean \
	--jobs=$N_JOBS \
	--port=$DB_PORT \
	--username=$DB_USER \
	|| { echo DEPLOY FAILED; exit 1;}

echo -e "\nCreating db extensions..."
psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="
		CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
		CREATE EXTENSION IF NOT EXISTS unaccent;
		CREATE EXTENSION IF NOT EXISTS pg_trgm;
	" > /dev/null

echo -e "\nDrop any staged book table from previous deploy... "
psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="
		DROP TABLE IF EXISTS isbns CASCADE;
		DROP TABLE IF EXISTS translations CASCADE;
		DROP TABLE IF EXISTS contents CASCADE;
		DROP TABLE IF EXISTS more_images CASCADE;
		DROP TABLE IF EXISTS words CASCADE;
		DROP TABLE IF EXISTS books CASCADE;
	" > /dev/null

echo -e "\nDropping old $APP_DB tables..."

psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="
		DROP TABLE IF EXISTS recsys_isbns;
		DROP TABLE IF EXISTS recsys_translations;
		DROP TABLE IF EXISTS recsys_contents;
		DROP TABLE IF EXISTS recsys_more_images;
		DROP TABLE IF EXISTS recsys_words;
		DROP TABLE IF EXISTS recsys_books;
	" || { echo DEPLOY FAILED; exit 1;}

echo -e "\nWriting new version of book tables to $APP_DB..."
pg_restore \
	/tmp/recsysetl \
	--dbname=$APP_DB \
	--clean \
	--if-exists \
	--jobs=$N_JOBS \
	--port=$DB_PORT \
	--username=$DB_USER \
	|| { echo DEPLOY FAILED; exit 1;}

echo -e "\nChanging table names to the ones Django expects..."
psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="
		ALTER TABLE books RENAME TO recsys_books;
		ALTER TABLE isbns RENAME TO recsys_isbns;
		ALTER TABLE translations RENAME TO recsys_translations;
		ALTER TABLE contents RENAME TO recsys_contents;
		ALTER TABLE more_images RENAME TO recsys_more_images;
		ALTER TABLE words RENAME TO recsys_words;
	" || { echo DEPLOY FAILED; exit 1;}

echo -e "\nChanging column names to the ones Django expects..."
psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="
		ALTER TABLE recsys_books RENAME COLUMN title_id to id;
		ALTER TABLE recsys_translations RENAME COLUMN title_id to id;
	" || { echo DEPLOY FAILED; exit 1;}

echo -e "\nAnalyzing..."
psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="ANALYZE"

echo -e "\nDEPLOY SUCCEEDED"

echo -e "\nChecking for orphaned ratings..."
psql \
	--dbname=$APP_DB \
	--port=$DB_PORT \
	--username=$DB_USER \
	--command="
		SELECT DISTINCT book_id 
		FROM recsys_rating 
		WHERE NOT EXISTS (
			SELECT 1 
			FROM recsys_books 
			WHERE id = recsys_rating.book_id
		);
	"
echo -e "If this query had results, research the history of 
the title ID(s) on isfdb.org and delete or update the rating(s)."

exit 1
