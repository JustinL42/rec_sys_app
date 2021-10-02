import os, sys
import pickle

from sqlalchemy import create_engine
import pandas as pd
from scipy.stats import truncnorm
from surprise import Dataset, Reader
from surprise.model_selection import GridSearchCV

from customSurpriseClasses import JumpStartKFolds, DefaultlessSVD

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)
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


def tune_svd_model():
    alchemyEngine = create_engine(db_conn_string)
    conn = alchemyEngine.connect()

    small_df = pd.read_sql("""
        SELECT r.user_id, r.book_id, r.rating
        FROM recsys_rating as r
        JOIN recsys_user as u ON u.id = r.user_id
        LEFT JOIN recsys_book_club_members as m ON m.user_id = u.id
        LEFT JOIN recsys_book_club as c ON c.id = m.book_club_id
        WHERE c.id != %s
        AND rating is not NULL
        AND u.virtual = FALSE;
        """, conn, params=[BX_BOOK_CLUB_ID])

    large_df = pd.read_sql("""
        SELECT r.user_id, r.book_id, r.rating 
        FROM recsys_rating as r
        JOIN recsys_user as u ON u.id = r.user_id
        LEFT JOIN recsys_book_club_members as m ON m.user_id = u.id
        LEFT JOIN recsys_book_club as c ON c.id = m.book_club_id
        WHERE c.id = %s
        AND rating is not NULL
        AND u.virtual = FALSE;
        """, conn, params=[BX_BOOK_CLUB_ID])

    df = pd.concat([small_df, large_df])

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
        """, [len(df), last_rating]).fetchone()

    print(svd_timestamps)
    if svd_timestamps:
        last_rating_timestamp = conn.execute("""
            SELECT last_updated 
            FROM recsys_rating
            WHERE rating IS NOT NULL
            ORDER BY last_updated DESC
            LIMIT 1;
        """).fetchone()

        print(last_rating_timestamp)

        if last_rating_timestamp and \
            svd_timestamps[0] > last_rating_timestamp[0]:

            # A model has already been tuned and stored since the last 
            # ratings update. Use this existing model instead of tuning.
            conn.close()
            print("no updates")
            return

    try:
        last_params = pickle.loads(conn.execute("""
            SELECT params_bin 
            FROM recsys_svdmodel
            ORDER BY time_created DESC
            LIMIT 1;
        """).fetchone()[0])

    except IndexError:
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

    param_distribution = {}
    for param, value in last_params.items():
        if param in ['biased', 'random_state']:
            param_distribution[param] = [value]
        elif param in ['n_factors', 'n_epochs']:
            param_distribution[param] = 
                [max(0, value - 5), value, value + 5]
        else:
            param_distribution[param] = truncnorm(
                loc=value, scale=(.1 * value), a=0, b=(1000 * value)
            )


    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df, reader)
    small_data = Dataset.load_from_df(small_df, reader)
    large_data = Dataset.load_from_df(large_df, reader)
    

def update_all_recs():
    pass

def tune_update_all_recs():
    tune_svd_model()
    update_all_recs()

def update_one_users_recs(id):
    pass