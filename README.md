# Recommendation System for Book Clubs

Currently online at:

https://bookclub.guide

A web app for users to browse and rate books from the science-fiction, fantasy, and speculative fiction genres. The current site is under development and signups aren't currently available to the public. Non-signed in visitors can still search the catalog, which is derived from the isfdb.org data (see my isfdb_migration repository). 

Current development is focused on adding a recommendation system to recommend new books to individual users, and groups of users reading together in book clubs. This would use the Surprise python library to run the SVD algorith on submitted user ratings, as well as public book rating data sets like Book Crossings. A prototype of this is in my earlier book_club_rec_system repository.

Copyright 2021 Justin Lavoie.
All rights reserved.