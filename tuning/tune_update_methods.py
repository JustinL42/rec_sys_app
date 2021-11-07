import os, sys
import pickle

from sqlalchemy import create_engine
import pandas as pd
from scipy.stats import truncnorm
from surprise import Dataset, Reader
from surprise.model_selection import RandomizedSearchCV


path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)
from customSurpriseClasses import JumpStartKFolds, DefaultlessSVD
from mysite import settings
from mysite import secret_keys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
import django
django.setup()
from recsys.models import SVDModel, Book_Club

db_user = settings.DATABASES['default'].get('USER', 'postgres')
db_password = settings.DATABASES['default'].get('PASSWORD', ' ')
db_host = settings.DATABASES['default'].get('HOST', ' ')
db_port = settings.DATABASES['default'].get('PORT', '5432')
db_name = settings.DATABASES['default'].get('NAME', 'recsysdev')
db_conn_string = "postgresql+psycopg2://{}:{}@{}:{}/{}"\
    .format(db_user, db_password, db_host, db_port, db_name)

# The id of the Book Crossing "book club", who aren't real users
BX_BOOK_CLUB_ID = 7


def tune_svd_model(n_iter=10, force=False):
    alchemyEngine = create_engine(db_conn_string)
    conn = alchemyEngine.connect()

    small_df = pd.read_sql("""
        SELECT r.user_id, r.book_id, r.rating
        FROM recsys_rating as r
        JOIN recsys_user as u ON u.id = r.user_id
        WHERE NOT EXISTS 
        (
          SELECT 1 
            FROM recsys_book_club_members AS m
            JOIN recsys_book_club AS c ON c.id = m.book_club_id
            WHERE c.id = %s
            AND m.user_id = u.id
        )
        AND u.virtual = FALSE
        AND r.rating IS NOT NULL;
        """, conn, params=[BX_BOOK_CLUB_ID])

    large_df = pd.read_sql("""
        SELECT r.user_id, r.book_id, r.rating 
        FROM recsys_rating as r
        JOIN recsys_user as u ON u.id = r.user_id
        JOIN recsys_book_club_members as m ON m.user_id = u.id
        JOIN recsys_book_club as c ON c.id = m.book_club_id
        WHERE c.id = %s
        AND rating is not NULL
        AND u.virtual = FALSE;
        """, conn, params=[BX_BOOK_CLUB_ID])

    df = pd.concat([small_df, large_df])
    num_ratings = len(df)

    last_rating = conn.execute("""
        SELECT id 
        FROM recsys_rating
        where rating IS NOT NULL
        ORDER BY last_updated DESC 
        LIMIT 1;
        """).fetchone()[0]

    # Check if any ratings have changed since the last time 
    # tune_svd_model was run
    svd_timestamps = conn.execute("""
        SELECT time_created 
        FROM recsys_svdmodel
        WHERE ratings = %s
        AND last_rating = %s
        ORDER BY time_created DESC 
        LIMIT 1;
        """, [num_ratings, last_rating]).fetchone()

    if not force and svd_timestamps:
        last_rating_timestamp = conn.execute("""
            SELECT last_updated 
            FROM recsys_rating
            WHERE rating IS NOT NULL
            ORDER BY last_updated DESC
            LIMIT 1;
            """).fetchone()

        if last_rating_timestamp and \
            svd_timestamps[0] > last_rating_timestamp[0]:

            # A model has already been tuned and stored since the last 
            # ratings update. Use this existing model instead of tuning.
            conn.close()
            return num_ratings, last_rating

    try:
        last_params = pickle.loads(conn.execute("""
            SELECT params_bin 
            FROM recsys_svdmodel
            WHERE ratings = %s
            AND last_rating = %s
            ORDER BY rmse, time_created DESC
            LIMIT 1;
            """).fetchone()[0])

    except TypeError:
        last_params = {
            'random_state': 777,
            'biased': True,
            'n_factors': 30,
            'n_epochs': 40,
            'lr_pu': 0.01,
            'lr_bu': 0.01,
            'lr_bi': 0.003,
            'lr_qi': 0.01,
            'reg_bu': 0.01,
            'reg_bi': 0.15,
            'reg_pu': 0.5,
            'reg_qi': 0.25
        }

    conn.close()

    param_distributions = {}
    for param, value in last_params.items():
        if param in ['biased', 'random_state']:
            param_distributions[param] = [value]
        elif param in ['n_factors', 'n_epochs']:
            param_distributions[param] = \
                [max(0, value - 5), value, value + 5]
        else:
            param_distributions[param] = truncnorm(
                loc=value, scale=(.1 * value), a=0, b=(1000 * value)
            )

    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df, reader)
    small_data = Dataset.load_from_df(small_df, reader)
    large_data = Dataset.load_from_df(large_df, reader)

    rs = RandomizedSearchCV(DefaultlessSVD, param_distributions, 
        n_iter=n_iter, 
        measures=['rmse'], 
        cv=JumpStartKFolds(large_data=large_data),
        refit=False,
        n_jobs=-2, 
        random_state=param_distributions.get('random_state', [777])[0]
    )
    rs.fit(small_data)
    best_model = rs.best_estimator['rmse']
    best_model.fit(data.build_full_trainset())

    ##### ^^ confirm this ^^^ ###


    # Save the new model to the database
    model_obj = SVDModel()
    model_obj.ratings = num_ratings
    model_obj.last_rating = last_rating
    model_obj.factors = rs.best_params['rmse']['n_factors']
    model_obj.rmse = rs.best_score['rmse']
    model_obj.params_bin = pickle.dumps(rs.best_params['rmse'])
    model_obj.model_bin = pickle.dumps(best_model)
    model_obj.save()

    return num_ratings, last_rating


def tune_n_times(n, n_iter=10):
    for i in range(n):
        tune_svd_model(n_iter, force=True)


def update_all_recs(num_ratings, last_rating):
    alchemyEngine = create_engine(db_conn_string)
    conn = alchemyEngine.connect()

    try:
        svd_model = pickle.loads(conn.execute("""
            SELECT model_bin
            FROM recsys_svdmodel
            WHERE ratings = %s
            AND last_rating = %s
            ORDER BY time_created DESC 
            LIMIT 1;
            """, [num_ratings, last_rating]).fetchone()[0])
    except TypeError:
        #TODO: log error "No SVD model found for the give ratings set"
        print("No SVD model found for the give ratings set")
        conn.close()
        return

    real_users = conn.execute("""
        SELECT u.id
        FROM recsys_user AS u
        WHERE virtual = FALSE
        AND NOT EXISTS 
        (
            SELECT 1 
                FROM recsys_book_club_members AS m
                JOIN recsys_book_club AS c ON c.id = m.book_club_id
                WHERE c.id = %s
                AND m.user_id = u.id
        );
    """, [BX_BOOK_CLUB_ID]).fetchall()

    conn.close()

    if not real_users:
        return
    real_user_set = set([u[0] for u in real_users])
    all_users = [
        (u, svd_model.trainset.to_raw_uid(u)) \
        for u in svd_model.trainset.all_users() \
        if svd_model.trainset.to_raw_uid(u) in real_user_set
    ]
    all_books = [
        (b, svd_model.trainset.to_raw_iid(b)) \
        for b in svd_model.trainset.all_items()
    ]

    for uid, user_id in all_users:
        conn = alchemyEngine.connect()

        # Set all current predictions to null before the update
        conn.execute("""
        UPDATE recsys_rating  
        SET predicted_rating = NULL
        WHERE user_id = %s;
        """, [user_id])

        for iid, title_id in all_books:
            prediction = svd_model.predict(uid, iid, clip=False).est

            conn.execute("""
                INSERT INTO recsys_rating 
                (book_id, user_id, predicted_rating, 
                    saved, blocked, last_updated)
                VALUES (%s, %s, %s, FALSE, FALSE, CURRENT_TIMESTAMP)
                ON CONFLICT (book_id, user_id)
                DO UPDATE SET predicted_rating = %s
            """, [title_id, user_id, prediction, prediction])
        conn.close()


def update_one_book_club_recs(book_club_id):
    alchemyEngine = create_engine(db_conn_string)
    conn = alchemyEngine.connect()
    df = pd.read_sql("""
        SELECT r.book_id, 
            AVG(COALESCE(r.rating, r.predicted_rating)) as avg_rating 
        FROM recsys_rating AS r
        JOIN recsys_user AS u ON u.id = r.user_id
        JOIN recsys_book_club_members AS m ON m.user_id = u.id
        JOIN recsys_book_club AS c ON c.id = m.book_club_id
        WHERE c.id = %s
        AND (
            r.predicted_rating IS NOT NULL
            OR r.rating IS NOT NULL
        )
        AND u.virtual = FALSE
        GROUP BY r.book_id
        HAVING COUNT(r.user_id) > 1;
        """, conn, params=[book_club_id])

    virtual_member_id = conn.execute("""
        SELECT virtual_member_id
        FROM recsys_book_club
        WHERE id = %s; 
        """, [book_club_id]).fetchone()[0]

    if not virtual_member_id:
        #TODO: log this error
        return

    # Set all current predictions to null before the update
    conn.execute("""
        DELETE
        FROM recsys_rating
        WHERE user_id = %s;
        """, [virtual_member_id])

    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO recsys_rating 
            (book_id, user_id, predicted_rating, 
                saved, blocked, last_updated)
            VALUES (%s, %s, %s, FALSE, FALSE, CURRENT_TIMESTAMP);
        """, [int(row['book_id']), 
            virtual_member_id, row['avg_rating']])

    conn.close()


def update_all_book_club_recs():
    alchemyEngine = create_engine(db_conn_string)
    conn = alchemyEngine.connect()
    book_clubs = conn.execute("""
        SELECT id
        FROM recsys_book_club
        WHERE virtual = FALSE;
    """).fetchall()
    conn.close()
    for book_club in book_clubs:
        update_one_book_club_recs(book_club[0])


def tune_update_all_recs():
    ratings, last_rating = tune_svd_model()
    update_all_recs(ratings, last_rating)
    update_all_book_club_recs()


def update_one_users_recs(user_id, top_n=None, bottom_n=None, 
        urgent=False, cold_start=False):
    alchemyEngine = create_engine(db_conn_string)
    conn = alchemyEngine.connect()

    try:
        svd_model = pickle.loads(conn.execute("""
            SELECT model_bin 
            FROM recsys_svdmodel
            ORDER BY time_created DESC
            LIMIT 1;
            """).fetchone()[0])

    except TypeError:
        #TODO: log error "No SVD models have been tuned yet"
        print("No SVD model found for the give ratings set")
        conn.close()
        return

    if urgent:
        svd_model.n_epochs = max(10, int(svd_model.n_epochs / 2))
    df = pd.read_sql("""
        SELECT r.user_id, r.book_id, r.rating 
        FROM recsys_rating AS r
        JOIN recsys_user AS u ON u.id = r.user_id
        WHERE r.rating IS NOT NULL
        AND u.virtual = FALSE;
        """, conn)
    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df, reader)

    svd_model.fit(data.build_full_trainset())

    uid = svd_model.trainset.to_inner_uid(user_id)
    all_books = [
        (b, svd_model.trainset.to_raw_iid(b)) \
        for b in svd_model.trainset.all_items()
    ]

    # Set all current predictions to null before the update
    conn.execute("""
    UPDATE recsys_rating
    SET predicted_rating = NULL
    WHERE user_id = %s;
    """, [user_id])

    predictions = []
    if not cold_start:
        for iid, title_id in all_books:
            prediction = svd_model.predict(uid, iid, clip=False).est
            predictions.append((prediction, title_id))
    else:
        cold_start_ids = set([ i[0] for i in conn.execute("""
            SELECT id
            FROM recsys_books
            WHERE cold_start_rank IS NOT NULL
            AND cold_start_rank <= 150
            """)])

        for iid, title_id in all_books:
            if title_id not in cold_start_ids:
                continue
            prediction = svd_model.predict(uid, iid, clip=False).est
            predictions.append((prediction, title_id))


    if top_n or bottom_n:
        predictions.sort(reverse=True)

        predictions = predictions[0:(top_n or 0)] + \
            predictions[(-bottom_n if bottom_n else len(predictions)):]

    for (prediction, title_id) in predictions:
        conn.execute("""
            INSERT INTO recsys_rating 
            (book_id, user_id, predicted_rating, 
                saved, blocked, last_updated)
            VALUES (%s, %s, %s, FALSE, FALSE, CURRENT_TIMESTAMP)
            ON CONFLICT (book_id, user_id)
            DO UPDATE SET predicted_rating = %s
        """, [title_id, user_id, prediction, prediction])
    conn.close()
