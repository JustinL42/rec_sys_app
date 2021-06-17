#!/bin/bash
pg_dump --format=custom --verbose --no-owner -d recsyslive -p 5432 -U postgres --data-only --table '(django_admin_log|django_content_type|auth_(group|permission|group_permissions)|recsys_(book_club|book_club_members|dataproblem|meeting|user|user_groups|user_user_permissions|rating))' -f backup/$(date --iso-8601=seconds).dump
