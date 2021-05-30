#!/usr/bin/python3
import os, sys, csv, zipfile
from urllib import request
import psycopg2

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)

from mysite import settings
from mysite import secret_keys


db_name = settings.DATABASES['default'].get('NAME', 'recsysdev')
db_port = settings.DATABASES['default'].get('PORT', '5432')
db_user = settings.DATABASES['default'].get('USER', 'postgres')
db_password = settings.DATABASES['default'].get('PASSWORD', ' ')
db_host = settings.DATABASES['default'].get('HOST', ' ')
db_conn_string = "dbname={} port={} user={} password= {} host={} "\
    .format(db_name, db_port, db_user, db_password, db_host)

path_to_bx_data = os.path.join("data", "book_crossing")
path_to_zip = os.path.join(path_to_bx_data, "BX-CSV-Dump.zip")
zipDownloaded = os.path.isfile(path_to_zip)
filesUnzipped = \
    os.path.isfile(os.path.join(path_to_bx_data, "BX-Users.csv")) and \
    os.path.isfile(os.path.join(path_to_bx_data, "BX-Book-Ratings.csv"))


if not (zipDownloaded or filesUnzipped):
    try:
        os.mkdir(path_to_bx_data)
    except FileExistsError:
        pass
    dataURL = \
        "http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip"
    print("Fetching zip file...")

    # the download command is commented out to prevent unintentional 
    # traffic to the site. 
    # Uncomment the following line if actually fetching the data.
    # request.urlretrieve(dataURL, path_to_zip)

if not filesUnzipped:
    try:
        zipObj = zipfile.ZipFile(path_to_zip)
    except FileNotFoundError:
        errorMessage = (
        "ERROR: The data set zip file isn't in the current "
        "directory.\nTo use this script to download it, uncomment "
        "the 'request.urlretrieve' line, "
        "or download it manually from: \n"
        "http://www2.informatik.uni-freiburg.de/~cziegler/BX/")
        print(errorMessage)
        raise SystemExit
    print("Unzipping file...")
    zipObj.extractall(path=path_to_bx_data)
    zipObj.close()


# convert csv to utf-8, remove problem characters:
os.system("iconv -f ISO_8859-16 -t utf-8 {} > {}" \
    .format(
        os.path.join(path_to_bx_data, 'BX-Users.csv'),
        os.path.join(path_to_bx_data, 'utf-users.csv')
    )
)
os.system("iconv -f ISO_8859-16 -t utf-8 {} > {}" \
    .format(
        os.path.join(path_to_bx_data, 'BX-Book-Ratings.csv'),
        os.path.join(path_to_bx_data, 'utf-ratings.csv')
    )
)


conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            print("Loading user data...")
            with open(os.path.join(path_to_bx_data, 'utf-users.csv')) as u_csv:
                u_reader = csv.reader(
                    u_csv, delimiter=';', quotechar='"')
                # discard header
                next(u_reader, None)

                last_name = "BookCrossing"
                password = secret_keys.bx_user_hash
                is_active = False
                is_superuser = False
                is_staff = False
                date_joined = '2004-08-01'
                email = ''
                virtual = False

                member_ids = []
                for row in u_reader:
                    username = "bx" + row[0]
                    first_name = row[0]
                    location = row[1]
                    if location == "NULL":
                        location = None
                    age = row[2]
                    if age == "NULL":
                        age = None

                    cur.execute("""
                        INSERT INTO recsys_user 
                        (username, first_name, last_name, password, email, 
                            location, age, is_active, is_superuser, 
                            is_staff, date_joined, virtual)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username)
                        DO UPDATE
                            SET first_name = EXCLUDED.first_name
                        RETURNING id;
                    """, (username, first_name, last_name, password, email, 
                            location, age, is_active, is_superuser, 
                            is_staff, date_joined, virtual)
                    )
                    member_ids.append(cur.fetchone()[0])

            # Create the virtual user, whose ratings are the 
            # average for the book crossings users as a whole
            username = "bx_virtual"
            first_name = "virtual"
            virtual = True
            location = None
            age = None
            cur.execute("""
                INSERT INTO recsys_user 
                (username, first_name, last_name, password, email, location, 
                age, is_active, is_superuser, is_staff, date_joined, virtual)
                VALUES (%s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) 
                DO UPDATE 
                SET first_name = EXCLUDED.first_name,
                    virtual = EXCLUDED.virtual
                RETURNING ID;
            """, (username, first_name, last_name, password, email, 
                    location, age, is_active, is_superuser, 
                    is_staff, date_joined, virtual)
            )
            virtual_user_id = cur.fetchone()[0]

            # delete any prior BookCrossing virtual book club
            cur.execute("""
                SELECT id
                FROM recsys_book_club
                WHERE name = %s;
            """, ("Book Crossings Virtual Book Club", )
            )
            existing_bx_clubs = cur.fetchall()
            for club in existing_bx_clubs:
                cur.execute("""
                    DELETE
                    FROM recsys_book_club_members
                    WHERE book_club_id = %s
                    """, (club)
                )
            cur.execute("""
                DELETE 
                FROM recsys_book_club
                WHERE name = %s;
                """, ("Book Crossings Virtual Book Club", )
            )

            # create the BookCrossing virtual book club
            cur.execute("""
                INSERT INTO recsys_book_club
                (name, virtual, virtual_member_id)
                VALUES (%s, %s, %s)
                RETURNING ID;
            """, ("Book Crossings Virtual Book Club", 
                    True, virtual_user_id)
            )

            # populate the virtual book club
            virtual_book_club_id = cur.fetchone()[0]
            for member_id in member_ids:
                cur.execute("""
                    INSERT INTO recsys_book_club_members
                    (book_club_id, user_id)
                    VALUES (%s, %s)
                """, (virtual_book_club_id, member_id)
                )

                # delete any pre-existing ratings for these users
                cur.execute("""
                    DELETE
                    FROM recsys_rating
                    where user_id = %s
                """, (member_id,))

            #TODO: update the virtual user's ratings
            # update_virtual_user("BookCrossing")


            print("Loading ratings data...")
            with open(
                os.path.join(path_to_bx_data, 'utf-ratings.csv')) as r_csv:
                
                r_reader = csv.reader(
                    r_csv, delimiter=';', quotechar='"')
                # discard header
                next(r_reader, None)

                saved = False
                blocked = False
                last_updated = '2004-08-01'

                ratings_dict = {}
                for row in r_reader:

                    # The bx data uses 0 for implicit ratings. Skip these.
                    rating = row[2]
                    if rating == '0':
                        continue

                    cur.execute("""
                        select title_id
                        from recsys_isbns
                        where isbn  = %s;
                        """, (row[1],)
                    )
                    book_id = cur.fetchone()
                    if not book_id:
                        continue

                    username = "bx" + row[0]
                    cur.execute("""
                        SELECT ID
                        FROM recsys_user
                        WHERE username = %s;
                        """, (username,)
                    )
                    user_id = cur.fetchone()[0]

                    ratings_dict[(book_id[0], user_id)] = \
                        ratings_dict.get((book_id[0], user_id), []) + \
                        [float(rating)]


                for (book_id, user_id), rating_list in ratings_dict.items():
                    # book_id, user_id = rating_tuple
                    rating = sum(rating_list)/len(rating_list)

                    cur.execute("""
                        INSERT INTO recsys_rating 
                        (rating, saved, blocked, last_updated, 
                            book_id, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (rating, saved, blocked, last_updated, 
                            book_id, user_id)
                    )

except Exception as e:
    raise e
finally:
    conn.close()
