Installation
==========================

These instructions have been tested on Fedora 40. Some details will be different on other platforms.

1. **Follow the [instructions to run the ISFDB migration script](https://github.com/JustinL42/isfdb_migration/blob/master/INSTALLATION.md).**<br>
   This should result in a copy of the book data being dumped up to Postgres directory backup at `/tmp/recsysetl`. If you ran the migration on another computer, you should copy the backup to the same directory on the current computer. The instructions in section 5 should still be followed to confirm Postgres is installed (version 13 or higher) and the OS user you intend to use to run the app has a Postgres user set up.
   
2. **Clone the repo and install the required dependencies.**<br>
   ~~~
   sudo dnf install libxslt-devel libxml2-devel
   git clone https://github.com/JustinL42/rec_sys_app
   cd rec_sys_app
   # Create a virual environment using your prefered method
   pip install .
   ~~~
   Optionally, install the development dependencies:
   ~~~
   pip install .[dev]
   ~~~

3. **Configure application parameters.**<br>
      Look at [`config/default.cfg`](config/default.cfg) to see explanations and defaults for each parameter. Then, look at [`dev.cfg`](config/dev.cfg) and [`prod.cfg`](config/prod.cfg). These both inherit any defaults that they don't override, and are examples of settings you may want to change on development or production systems. If you are setting up both dev and prod, I suggest setting the database names differently to avoid confusion about which one you are in when using the `psql` shell (e.g., `recsysdev` and`recsyslive`). I'll use the default `recsys` name in these instructions.
      An example minimal dev configuration could be:
      * `db_name` set to the database name you chose above.
      * `db_host` set explicitly to blank if you are using Postgres install on the local machine and connecting via unix socket.
      * `db_user` set to the OS/Postgres user you setup in the ISFDB migration instructions, who will be running the app.
      * `db_password` set explicitly to blank if you are using default `ident` authentication.

      Set your custom parameters in either `dev.cfg` or `prod.cfg`, or in your own [INI](https://en.wikipedia.org/wiki/INI_file) configuration file with a unique section header name. 
      To specify which configuration the script should use, set your shell's ENV variable to the file's section header name (which may differ from the filename). For instance:
   ~~~
   export ENV=DEV
   ~~~
   If you plan to run the app with the same configuration in the future, this line can be added to user's shell startup script (e.g. `.bashrc`) or the virtual environment's activation script (e.g. `.env/bin/activate`)

4. **Create the application's database and custom search configuration, run the initial migration, and load the book data.** <br>
The custom search configuration is needed so that queries for actual book titles like *IT* or *Them* aren't reduced to nothing by excessive removal of stop words. The [isfdb_title stopword list](https://github.com/JustinL42/isfdb_migration/blob/master/config/isfdb_title.stop) should already be installed as described in the isfdb migration instructions.<br>
   Use the name you set in the configuration above instead of `recsys`.
   ~~~
   createdb recsys

   psql --dbname=recsys --command="
      CREATE TEXT SEARCH DICTIONARY isfdb_title_dict (
          TEMPLATE = snowball,
          language = english,
          STOPWORDS = isfdb_title
      );
      CREATE TEXT SEARCH CONFIGURATION public.isfdb_title_tsc (
          COPY = pg_catalog.english
      );
      ALTER TEXT SEARCH CONFIGURATION public.isfdb_title_tsc
          ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
          WITH isfdb_title_dict;

      ALTER TEXT SEARCH CONFIGURATION public.isfdb_title_tsc
          DROP MAPPING FOR email, url, url_path, sfloat, float;"

   python manage.py makemigrations recsys
   python manage.py migrate
   scripts/deploy_new_books.sh

   ~~~

5. **Run the server.**<br>
   ~~~
   python manage.py runserver
   ~~~
   At this point, book browsing, searching, and user account creation should work, but recommendations can't be generated because no model has been trained. To do this, stop the server and follow the additional steps.

6. **Download and add the Book-Crossing user rating.**<br>
**Important Update:** The Book-Crossing data is no longer available at the url below. It's currently available [here](https://web.archive.org/web/20230319134511/http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip) through the Internet Archive, but is easier to download through your browser rather than with wget.
   ~~~
   wget http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip
   mkdir data/book_crossing
   cp BX-CSV-Dump.zip data/book_crossing/
   python data/load_book_crossings.py
   ~~~
   These ratings are associated with "virtual users" who won't actually be logging into the site, but whose data helps jump-start model tuning even when you have relatively few real users.

7. **Add real user data.**<br>
   The customized training algorithm requires some number (preferable more than twenty or so) of real users, each with a significant number of ratings. The algorithm favors candidate models that predict the real users' ratings accurately, though both real and virtual users' data helps create the model. My real users' data isn't included in this repository. The `data/load_custom.py` script was used to load a book club's rating data from a CSV file. It could be used as a general idea of how to do this with your own data. The `data/load_goodreads.py` script can be used to load a user's data from an export of their goodreads.com rating data.

8. **Run the initial model tuning and assign predicted ratings.**<br>
   Enter the Django shell to access the tuning methods.
   ~~~
   python manage.py shell
   
   from tuning.tune_update_methods import tune_n_times
   tune_n_times(50)
   ~~~
   You can run the tuning for more iterations if you would like and if the RMSE continues to decline. 
   To use the model to assign recommendations to users, you will first need to get two numbers the app uses to identify the version of the data the model was trained on: the total number of ratings and the ID of the last rating. To get these:
   ~~~
   psql \
   --dbname=recsys \
   --command="
      SELECT ratings, last_rating
      FROM recsys_svdmodel
      ORDER BY time_created DESC
      LIMIT 1;"
   ~~~

   Then, return to the Django shell:
   ~~~
   python manage.py shell

   from tuning.tune_update_methods import update_all_recs
   # syntax: update_all_recs(ratings, last_rating)
   update_all_recs(2222, 2345)
   ~~~
   Users should now have their highest ranked recommendations on their "Recommendations" page.