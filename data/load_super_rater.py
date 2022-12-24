#!/usr/bin/python3
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

import pandas as pd
import psycopg2

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)

from data.super_rater.title_handling import title_override, titles_to_skip

# On a dry run, print the book found for the title
# and do everything except actually inserting the data into
DRY_RUN = False
FILES = ["super_rater/SFRatings-N", "super_rater/SFRatings-AC"]
ORIGINAL_MIN = 1
ORIGINAL_MAX = 13
conversion = lambda r: max(1, min(10, r * 3 / 4 + 1 / 4))

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

data_dir = os.path.dirname(os.path.realpath(__file__))
rows = []
for file in FILES:
    filename = os.path.join(data_dir, file)
    with open(filename) as f:
        filerows = f.readlines()
    rows += filerows

count = defaultdict(lambda: 0)
ratings_dict = {}
needs_review = pd.DataFrame(
    columns=["title", "r_title", "r_authors", "authors", "year", "category"]
)

conn = psycopg2.connect(db_conn_string)
try:
    with conn:
        with conn.cursor() as cur:
            for row, index in zip(rows, range(len(rows))):
                if row[:5] in ["=====", "[834]", "[288]"]:
                    continue
                count["total"] += 1
                rating_and_authors, title = re.split(r" {3,}", row, maxsplit=1)
                title = (
                    re.sub(r"\\`", r"", re.sub(r"\\'", r"", title))
                    .replace("\\", "")
                    .strip()
                )

                if title in titles_to_skip:
                    count["titles_skipped"] += 1
                    continue

                rating = int(rating_and_authors[:3])
                authors = re.sub(
                    r"\\`", r"", re.sub(r"\\'", r"", rating_and_authors[3:])
                )
                authors = authors.split("+")
                author_list = []
                for author in authors:
                    author_names = author.split(",")
                    try:
                        author_full_name = (
                            author_names[1] + " " + author_names[0]
                        )
                    except IndexError:
                        author_full_name = author_names[0]
                    author_list.append(author_full_name)
                author_str = ", ".join(author_list)
                author_set = set([a.lower() for a in author_list])

                try:
                    title_id = title_override[title]

                    # In one ambiguous case,
                    # the id's entry is a tuple instead of an int
                    if title == "The Best of John W. Campbell":
                        if (
                            author_str
                            == "John W. Campbell Jr., Lester del Rey"
                        ):
                            title_id = title_id[1]
                        else:
                            title_id = title_id[0]
                    elif title == "Wizards":
                        if author_str == "Jack Dann, Gardner Dozois":
                            title_id = title_id[1]
                        else:
                            title_id = title_id[0]
                    elif title == "New Dimensions 1":
                        if author_str == "Robert Silverberg, Marta Randall":
                            count["titles_skipped"] += 1
                            continue
                        else:
                            title_id = title_id[0]

                    # put title_id in list if it isn't already:
                    try:
                        title_id = [int(title_id)]
                    except TypeError:
                        pass

                    for one_title_id in title_id:
                        rating_list, year, original_id_set = ratings_dict.get(
                            one_title_id, ([], None, set())
                        )
                        rating_list.append(rating)
                        original_id_set.add(
                            '"{}" by {}'.format(title, author_str)
                        )
                        ratings_dict[one_title_id] = (
                            rating_list,
                            index,
                            original_id_set,
                        )

                    count["handled_by_override"] += 1
                    continue
                except KeyError:
                    pass

                cur.execute(
                    """
                    SELECT id, unaccent(title), unaccent(authors), 
                        year, book_type
                    FROM recsys_books
                    WHERE general_search @@ 
                        websearch_to_tsquery('isfdb_title_tsc', %s )
                    ORDER BY 
                        CASE 
                            WHEN (LOWER(unaccent(title)) = LOWER(%s))
                                AND (LOWER(unaccent(authors)) = LOWER(%s)) 
                                    THEN (2 + editions)
                            WHEN (LOWER(unaccent(title)) = LOWER(%s)) THEN 1
                            ELSE 0
                        END DESC,
                        ts_rank_cd(general_search, 
                            websearch_to_tsquery('isfdb_title_tsc', %s
                        ), 8) DESC, 
                        editions DESC,
                        id ASC;
                """,
                    (title, title, author_str, title, title),
                )
                results = cur.fetchall()

                if not results:
                    category = "no_matches"
                    needs_review = needs_review.append(
                        {
                            "title": title,
                            "authors": author_str,
                            "category": category,
                        },
                        ignore_index=True,
                    )

                    count[category] += 1
                    continue

                r_id, r_title, r_authors, r_year, r_type = results[0]
                r_author_set = set(r_authors.lower().split(", "))

                rating_list, year, original_id_set = ratings_dict.get(
                    r_id, ([], None, set())
                )
                rating_list.append(rating)
                original_id_set.add('"{}" by {}'.format(title, author_str))
                ratings_dict[r_id] = (rating_list, index, original_id_set)

                exact_title_match = r_title.lower() == title.lower()
                exact_author_match = r_author_set == author_set

                if len(results) == 1:
                    if exact_title_match and exact_author_match:
                        # not manually verified, but assumed correct.
                        count["unique_exact_title_and_author"] += 1
                        continue
                    elif exact_title_match:
                        # All these cases are verified to be correct
                        category = "unique_exact_title"
                    else:
                        # All these cases are verified to be either correct
                        # or are manually handled.
                        category = "single_non_exact_match"

                    needs_review = needs_review.append(
                        {
                            "title": title,
                            "authors": author_str,
                            "year": results[0][3],
                            "r_title": results[0][1],
                            "r_authors": results[0][2],
                            "r_type": results[0][4],
                            "category": category,
                        },
                        ignore_index=True,
                    )
                    count[category] += 1
                    continue

                # Is it the only exact title match in the results?
                only_exact = True
                for secondary_result in results[1:]:
                    if title.lower() == secondary_result[
                        1
                    ].lower() and author_set == set(
                        [a for a in secondary_result[2].lower().split(", ")]
                    ):

                        only_exact = False
                        break

                if exact_title_match and exact_author_match and only_exact:
                    # Accepting the first result on all of these
                    category = "first_only_exact_title_and_author"
                elif (
                    exact_title_match and exact_author_match and not only_exact
                ):
                    category = "first_among_exact_title_and_author"
                elif exact_title_match and only_exact:
                    category = "first_only_exact_title"
                elif exact_title_match and not only_exact:
                    category = "first_among_exact_title"
                elif not only_exact:
                    category = "first_among_exact_title"
                else:
                    category = "no_exact_matches"

                needs_review = needs_review.append(
                    {
                        "title": title,
                        "authors": author_str,
                        "year": "\n".join([str(r[3]) for r in results]),
                        "r_title": "\n".join([r[1] for r in results]),
                        "r_authors": "\n".join([r[2] for r in results]),
                        "r_type": "\n".join([r[4] for r in results]),
                        "category": category,
                    },
                    ignore_index=True,
                )
                count[category] += 1

            last_name = ""
            password = config["custom_user_hash"]
            is_active = False
            is_superuser = False
            is_staff = False
            date_joined = datetime.now()
            email = ""
            virtual = False
            if not DRY_RUN:
                cur.execute(
                    """
                    INSERT INTO recsys_user 
                    (username, first_name, last_name, password, email,
                        is_active, is_superuser, is_staff, 
                        date_joined, virtual)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username) 
                    DO UPDATE 
                    SET first_name = EXCLUDED.first_name,
                        date_joined = EXCLUDED.date_joined
                    RETURNING ID;
                """,
                    (
                        "Dave",
                        "Dave",
                        last_name,
                        password,
                        email,
                        is_active,
                        is_superuser,
                        is_staff,
                        date_joined,
                        virtual,
                    ),
                )
                user_id = cur.fetchone()[0]

                cur.execute(
                    """
                    DELETE
                    FROM recsys_rating
                    WHERE user_id = %s
                """,
                    (user_id,),
                )

            saved = False
            blocked = False
            for book_id, (rating_list, _, original_id_set) in sorted(
                ratings_dict.items(), key=lambda x: -x[1][1]
            ):

                rating = sum(rating_list) / len(rating_list)
                original_book_id = " ; ".join(sorted(original_id_set))

                if not DRY_RUN:
                    cur.execute(
                        """
                        INSERT INTO recsys_rating 
                        (rating, saved, blocked, last_updated, 
                            book_id, user_id, original_book_id,
                            original_rating, original_min, original_max)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            conversion(rating),
                            saved,
                            blocked,
                            datetime.now(),
                            book_id,
                            user_id,
                            original_book_id,
                            rating,
                            ORIGINAL_MIN,
                            ORIGINAL_MAX,
                        ),
                    )

except Exception as e:
    raise e
finally:
    conn.close()

for category, total in sorted(count.items(), key=lambda i: -i[1]):
    print("{}: {}".format(category, total))

needs_review.to_clipboard()

if count["handled_by_override"] < len(title_override):
    print(
        "WARNING: not all titles in title_override were processed. "
        + "Do they all match the titles in the source file exactly?"
    )
if count["titles_skipped"] < len(titles_to_skip):
    print(
        "WARNING: not all titles in title_to_skip were seen. "
        + "Do they all match the titles in the source file exactly?"
    )
