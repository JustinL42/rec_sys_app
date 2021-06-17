#!/bin/bash

psql -p 5432 -U postgres -d recsyslive -c "
DELETE FROM recsys_meeting;
DELETE FROM recsys_dataproblem;
DELETE FROM recsys_book_club;
DELETE FROM recsys_book_club_members;
DELETE FROM recsys_rating;
DELETE FROM recsys_user;
DELETE FROM recsys_user_groups;
DELETE FROM recsys_user_user_permissions;
DELETE FROM auth_group;
DELETE FROM auth_group_permissions;
DELETE FROM auth_permission;
DELETE FROM django_admin_log;
DELETE FROM django_content_type;
"

pg_restore --verbose -p 5432 -U postgres --data-only -d recsyslive $(ls -t backup/*.dump | head -1)

psql -p 5432 -U postgres -d recsyslive -c 'SELECT book_id FROM recsys_rating WHERE NOT EXISTS (SELECT 1 FROM recsys_books WHERE id = recsys_rating.book_id);'
# psql -p 5434 -U postgres -d recsysdev -c 'DELETE FROM recsys_rating WHERE NOT EXISTS (SELECT 1 FROM recsys_books WHERE id = recsys_rating.book_id);'
