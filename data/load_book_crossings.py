#!/usr/bin/python3
import configparser
import csv
import os
import sys
import zipfile
from pathlib import Path

import psycopg2

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(BASE_DIR)

INCONSISTENT_ISBN_VIRTUAL_TITLE = 73

# Get per-environment settings from the config files.
CONFIG_DIR = Path(BASE_DIR, "config")
CONFIG_FILES = [Path(CONFIG_DIR, f) for f in os.listdir(CONFIG_DIR)]
ENV = os.environ.get("ENV", "DEFAULT")
config_parser = configparser.ConfigParser()
config_parser.read(CONFIG_FILES)
config = config_parser[ENV]

db_conn_string = (
    f"dbname={config['NAME']} port={config['PORT']} "
    + f"user={config['USER']} password= {config['PASSWORD']} "
    + f"host={config['HOST']} "
)

path_to_bx_data = os.path.join("data", "book_crossing")
path_to_zip = os.path.join(path_to_bx_data, "BX-CSV-Dump.zip")
zipDownloaded = os.path.isfile(path_to_zip)
filesUnzipped = os.path.isfile(
    os.path.join(path_to_bx_data, "BX-Users.csv")
) and os.path.isfile(os.path.join(path_to_bx_data, "BX-Book-Ratings.csv"))


if not (zipDownloaded or filesUnzipped):
    try:
        os.mkdir(path_to_bx_data)
    except FileExistsError:
        pass
    dataURL = (
        "http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip"
    )
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
            "http://www2.informatik.uni-freiburg.de/~cziegler/BX/"
        )
        print(errorMessage)
        raise SystemExit
    print("Unzipping file...")
    zipObj.extractall(path=path_to_bx_data)
    zipObj.close()


# convert csv to utf-8, remove problem characters:
os.system(
    "iconv -f ISO_8859-16 -t utf-8 {} > {}".format(
        os.path.join(path_to_bx_data, "BX-Users.csv"),
        os.path.join(path_to_bx_data, "utf-users.csv"),
    )
)
os.system(
    "iconv -f ISO_8859-16 -t utf-8 {} > {}".format(
        os.path.join(path_to_bx_data, "BX-Book-Ratings.csv"),
        os.path.join(path_to_bx_data, "utf-ratings.csv"),
    )
)

# The isbn table will be used to map most isbns to title_ids. However,
# some of these are marked as ambiguous since they've been re-used for
# multiple books. In most of these cases, the intended book has been
# determined by looking at the BX-Books.csv file
bx_title_dict = {
    "0064405052": 1589,
    "0330016970": 25149,
    "0373638094": 12715,
    "0439169445": 1867874,
    "0441007015": 9847,
    "0451453026": 13244,
    "0671028065": 26947,
    "0671040707": 26274,
    "0671787551": 12360,
    "0671878468": 3719,
    "0765348446": 1055216,
    "0786851473": 155306,
    "0786913886": 19400,
    "0915442639": 2801,
    "0946626987": 980005,
}


conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:

            print("Loading user data...")
            with open(os.path.join(path_to_bx_data, "utf-users.csv")) as u_csv:
                u_reader = csv.reader(u_csv, delimiter=";", quotechar='"')
                # discard header
                next(u_reader, None)

                last_name = "BookCrossing"
                password = config["bx_user_hash"]
                is_active = False
                is_superuser = False
                is_staff = False
                date_joined = "2004-08-01"
                email = ""
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

                    cur.execute(
                        """
                        INSERT INTO recsys_user
                        (username, first_name, last_name, password, email,
                            location, age, is_active, is_superuser,
                            is_staff, date_joined, virtual)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username)
                        DO UPDATE
                            SET first_name = EXCLUDED.first_name
                        RETURNING id;
                    """,
                        (
                            username,
                            first_name,
                            last_name,
                            password,
                            email,
                            location,
                            age,
                            is_active,
                            is_superuser,
                            is_staff,
                            date_joined,
                            virtual,
                        ),
                    )
                    member_ids.append(cur.fetchone()[0])

            # Create the virtual user, whose ratings are the
            # average for the book crossings users as a whole
            username = "bx_virtual"
            first_name = "virtual"
            virtual = True
            location = None
            age = None
            cur.execute(
                """
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
            """,
                (
                    username,
                    first_name,
                    last_name,
                    password,
                    email,
                    location,
                    age,
                    is_active,
                    is_superuser,
                    is_staff,
                    date_joined,
                    virtual,
                ),
            )
            virtual_user_id = cur.fetchone()[0]

            # delete any prior BookCrossing virtual book club
            cur.execute(
                """
                SELECT id
                FROM recsys_book_club
                WHERE name = %s;
            """,
                ("Book Crossings Virtual Book Club",),
            )
            existing_bx_clubs = cur.fetchall()
            for club in existing_bx_clubs:
                cur.execute(
                    """
                    DELETE
                    FROM recsys_book_club_members
                    WHERE book_club_id = %s
                    """,
                    (club),
                )
            cur.execute(
                """
                DELETE
                FROM recsys_book_club
                WHERE name = %s;
                """,
                ("Book Crossings Virtual Book Club",),
            )

            # create the BookCrossing virtual book club
            cur.execute(
                """
                INSERT INTO recsys_book_club
                (name, virtual, virtual_member_id)
                VALUES (%s, %s, %s)
                RETURNING ID;
            """,
                ("Book Crossings Virtual Book Club", True, virtual_user_id),
            )

            # populate the virtual book club
            virtual_book_club_id = cur.fetchone()[0]
            for member_id in member_ids:
                cur.execute(
                    """
                    INSERT INTO recsys_book_club_members
                    (book_club_id, user_id)
                    VALUES (%s, %s)
                """,
                    (virtual_book_club_id, member_id),
                )

                # delete any pre-existing ratings for these users
                cur.execute(
                    """
                    DELETE
                    FROM recsys_rating
                    where user_id = %s
                """,
                    (member_id,),
                )

            # TODO: update the virtual user's ratings
            # update_virtual_user("BookCrossing")

            print("Loading ratings data...")
            with open(
                os.path.join(path_to_bx_data, "utf-ratings.csv")
            ) as r_csv:

                r_reader = csv.reader(r_csv, delimiter=";", quotechar='"')
                # discard header
                next(r_reader, None)

                saved = False
                blocked = False
                last_updated = "2004-08-01"

                ratings_dict = {}
                inconsistent_isbns = set()
                for row in r_reader:

                    # The bx data uses 0 for implicit ratings. Skip these.
                    rating = row[2]
                    if rating == "0":
                        continue
                    isbn = row[1]

                    cur.execute(
                        """
                        select title_id
                        from recsys_isbns
                        where isbn  = %s;
                        """,
                        (isbn,),
                    )
                    book_id = cur.fetchone()
                    if not book_id:
                        continue
                    elif book_id[0] == INCONSISTENT_ISBN_VIRTUAL_TITLE:
                        try:
                            book_id = [bx_title_dict[isbn]]
                        except KeyError:
                            inconsistent_isbns.add(isbn)
                            continue

                    username = "bx" + row[0]
                    cur.execute(
                        """
                        SELECT ID
                        FROM recsys_user
                        WHERE username = %s;
                        """,
                        (username,),
                    )
                    user_id = cur.fetchone()[0]

                    rating_list, isbns_set = ratings_dict.get(
                        (book_id[0], user_id), ([], set())
                    )
                    rating_list.append(float(rating))
                    isbns_set.add(isbn)
                    ratings_dict[(book_id[0], user_id)] = (
                        rating_list,
                        isbns_set,
                    )

                for (book_id, user_id), (
                    rating_list,
                    isbns_set,
                ) in ratings_dict.items():

                    rating = sum(rating_list) / len(rating_list)
                    original_book_id = ", ".join(sorted(isbns_set))

                    cur.execute(
                        """
                        INSERT INTO recsys_rating
                        (rating, saved, blocked, last_updated,
                            book_id, user_id, original_book_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                        (
                            rating,
                            saved,
                            blocked,
                            last_updated,
                            book_id,
                            user_id,
                            original_book_id,
                        ),
                    )

except Exception as e:
    raise e
finally:
    conn.close()

if inconsistent_isbns:
    print("Inconsistent isbns skipped: ")
    for isbn in sorted(inconsistent_isbns):
        print(isbn)
