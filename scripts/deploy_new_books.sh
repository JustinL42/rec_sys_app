#!/bin/bash

# Get settings from config files:
export $(python scripts/print_config.py )

# Number of jobs to use. Default is all but one.
if ! [[ -v $n_deploy_jobs ]]; then
	n_deploy_jobs=$(nproc --ignore=1)

echo -e "\nDumping $db_name db to /tmp/recsysold..."
rm -rf /tmp/recsysold 2> /dev/null
pg_dump \
	$db_name \
	--file=/tmp/recsysold \
	--format=directory \
	--jobs=$n_deploy_jobs \
	--port=$db_port \
	--username=$db_user \
	|| { echo DEPLOY FAILED; exit 1;}

echo -e "\nBacking up /tmp/recsysold to recsysold db..."
dropdb recsysold --if-exists --username=$db_user
createdb recsysold --template=$db_name --username=$db_user
pg_restore \
	/tmp/recsysold \
	--dbname=recsysold \
	--clean \
	--jobs=$n_deploy_jobs \
	--port=$db_port \
	--username=$db_user \
	|| { echo DEPLOY FAILED; exit 1;}

echo -e "\nCreating db extensions..."
psql \
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
	--command="
		CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
		CREATE EXTENSION IF NOT EXISTS unaccent;
		CREATE EXTENSION IF NOT EXISTS pg_trgm;
	" > /dev/null

echo -e "\nDrop any staged book table from previous deploy... "
psql \
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
	--command="
		DROP TABLE IF EXISTS isbns CASCADE;
		DROP TABLE IF EXISTS translations CASCADE;
		DROP TABLE IF EXISTS contents CASCADE;
		DROP TABLE IF EXISTS more_images CASCADE;
		DROP TABLE IF EXISTS words CASCADE;
		DROP TABLE IF EXISTS books CASCADE;
	" > /dev/null

echo -e "\nDropping old $db_name tables..."
psql \
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
	--command="
		DROP TABLE IF EXISTS recsys_isbns;
		DROP TABLE IF EXISTS recsys_translations;
		DROP TABLE IF EXISTS recsys_contents;
		DROP TABLE IF EXISTS recsys_more_images;
		DROP TABLE IF EXISTS recsys_words;
		DROP TABLE IF EXISTS recsys_books;
	" || { echo DEPLOY FAILED; exit 1;}

echo -e "\nWriting new version of book tables to $db_name..."
pg_restore \
	/tmp/recsysetl \
	--dbname=$db_name \
	--clean \
	--if-exists \
	--jobs=$n_deploy_jobs \
	--port=$db_port \
	--username=$db_user \
	|| { echo DEPLOY FAILED; exit 1;}

echo -e "\nChanging table names to the ones Django expects..."
psql \
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
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
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
	--command="
		ALTER TABLE recsys_books RENAME COLUMN title_id to id;
		ALTER TABLE recsys_translations RENAME COLUMN title_id to id;
	" || { echo DEPLOY FAILED; exit 1;}

echo -e "\nAnalyzing..."
psql \
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
	--command="ANALYZE"

echo -e "\nDEPLOY SUCCEEDED"

echo -e "\nChecking for orphaned ratings..."
psql \
	--dbname=$db_name \
	--port=$db_port \
	--username=$db_user \
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
