#!/usr/bin/python3

"""
Prototype code for tuning parameters and 
estimating ratings for book-user pairs.
"""

import os, sys
from surprise import SVD
from surprise import Dataset, Reader
from surprise.model_selection import GridSearchCV
from surprise import dump
import pickle
from customSurpriseClasses import JumpStartKFolds

from sqlalchemy import create_engine
import pandas as pd

class DefaultlessSVD(SVD):

    def default_prediction(self):
        print("Prediction Impossible")
        return None

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
import django
django.setup()
from recsys.models import SVDModel, Book_Club

REAL_BOOK_CLUB_ID = 8

print("Connecting to db and loading data into memory...")
alchemyEngine = create_engine(
    'postgresql+psycopg2://postgres:@:5432/recsysdev')
conn = alchemyEngine.connect()

small_df = pd.read_sql("""
    SELECT r.user_id, r.book_id, r.rating
    FROM recsys_rating as r
    JOIN recsys_user as u ON u.id = r.user_id
    LEFT JOIN recsys_book_club_members as m ON m.user_id = u.id
    LEFT JOIN recsys_book_club as c ON c.id = m.book_club_id
    WHERE c.id = %s;
    """, conn, params=[REAL_BOOK_CLUB_ID])

large_df = pd.read_sql("""
    SELECT r.user_id, r.book_id, r.rating 
    FROM recsys_rating as r
    JOIN recsys_user as u ON u.id = r.user_id
    LEFT JOIN recsys_book_club_members as m ON m.user_id = u.id
    LEFT JOIN recsys_book_club as c ON c.id = m.book_club_id
    WHERE c.id != %s;
    """, conn, params=[REAL_BOOK_CLUB_ID])

df = pd.read_sql("""
    SELECT user_id, book_id, rating
    FROM recsys_rating
    WHERE rating is not NULL;
    """, conn)

last_rating = conn.execute("""
    SELECT id 
    FROM recsys_rating 
    ORDER BY id DESC 
    LIMIT 1;
    """).fetchone()[0]

rmse_to_beat = conn.execute("""
    SELECT rmse 
    FROM recsys_svdmodel
    WHERE ratings = %s
    AND last_rating = %s
    ORDER BY rmse ASC, time_created DESC 
    LIMIT 1;
    """, [len(df), last_rating]).fetchone()

if rmse_to_beat:
    rmse_to_beat = rmse_to_beat[0]
else:
    rmse_to_beat = 9999

params_to_beat = conn.execute("""
    SELECT params_bin 
    FROM recsys_svdmodel
    WHERE ratings = %s
    AND last_rating = %s
    ORDER BY rmse ASC, time_created DESC
    LIMIT 1;
    """, [len(df), last_rating]).fetchone()

if params_to_beat:
    params_to_beat = pickle.loads(params_to_beat[0])


try:
    title_dict = pickle.load(open("title_dict.pickle", "rb"))
except FileNotFoundError:
    title_df = pd.read_sql("""
        SELECT id, title
        FROM recsys_books;
        """, conn)
    print("Populating title dictionary...")
    title_dict = {}
    for row in title_df.iterrows():
        title_dict[row[1].id] = row[1].title
    pickle.dump(title_dict, open("title_dict.pickle", "wb"))


conn.close()

reader = Reader(rating_scale=(1, 10))
data = Dataset.load_from_df(df, reader)
small_data = Dataset.load_from_df(small_df, reader)
large_data = Dataset.load_from_df(large_df, reader)

param_grid = {
    'random_state': [777],
    'biased': [True], 
    'n_factors': [30],
    'n_epochs': [40], 

    # 'lr_all': [0.005],

    # 'lr_pu': [0.001, 0.01, 0.1],
    'lr_pu': [0.01],

    # 'lr_bu': [0.001, 0.01, 0.1],
    'lr_bu': [0.01],

    # 'lr_bi': [0.001, 0.003, 0.005],
    'lr_bi': [0.003],

    # 'lr_qi': [0.001, 0.01, 0.1],
    'lr_qi': [0.01],


    # 'reg_all': [0.07, 0.1, 0.3],

    'reg_bu': [0.01],
    # 'reg_bu': [0.001, 0.01, 0.1],

    'reg_bi': [0.15],
    # 'reg_bi': [0.15, 0.2, 0.25],
    
    'reg_pu': [0.5],
    # 'reg_pu': [0.3, 0.5, 0.7],

    'reg_qi': [0.25],
    # 'reg_qi': [.25, .5, .75],

    
}

print("Gridsearch...")
gs = GridSearchCV(
    DefaultlessSVD, param_grid, measures=['rmse'], cv=3, n_jobs = -2)

gs.fit(data)

# best RMSE score
print(gs.best_score['rmse'])
print(gs.best_params)

# combination of parameters that gave the best RMSE score
best_rmse = gs.best_score['rmse']
print(best_rmse)

algo = gs.best_estimator['rmse']
print("Fitting and dumping algorithm...")
algo.fit(data.build_full_trainset())


# dump.dump('test.dump', algo=algo)
# algo2 = dump.load('test.dump')[1]

# My own user id
USER_ID = 557924
# A title id that should be estimated with a positive rating
TITLE_ID = 1475

uid = algo.trainset.to_inner_uid(USER_ID)
iid = algo.trainset.to_inner_iid(TITLE_ID)

print(algo.predict(uid, iid, clip=False).est)
# print(algo2.predict(uid, iid, clip=False).est)

all_ratings = [
    (
        algo.trainset.to_raw_iid(x), 
        title_dict.get(algo.trainset.to_raw_iid(x), "Title Unknown"), 
        algo.predict(uid, x, clip=False).est
    ) for x in algo.trainset.all_items()
]

r_df = pd.DataFrame(all_ratings)
r_df.sort_values(by=2, ascending=False, inplace=True)


if best_rmse > rmse_to_beat:
    sys.exit()

print("A new record")
print(r_df[[1,2]].head(10))

# Save the new model to the database
model_obj = SVDModel()
model_obj.ratings = len(df)
model_obj.last_rating = last_rating
model_obj.factors = gs.best_params['rmse']['n_factors']
model_obj.rmse = best_rmse
model_obj.book_club = Book_Club.objects.get(id=REAL_BOOK_CLUB_ID)
model_obj.params_bin = pickle.dumps(gs.best_params['rmse'])
model_obj.model_bin = pickle.dumps(gs.best_estimator['rmse'])
model_obj.save()

#Update USER_ID's ratings
conn = alchemyEngine.connect()
conn.execute("""
    UPDATE recsys_rating  
    SET predicted_rating = NULL
    WHERE ID = %s;
    """, [USER_ID])

for row_id, (title_id, title, prediction) in r_df.iterrows():
    conn.execute("""
        INSERT INTO recsys_rating 
            (book_id, user_id, predicted_rating, saved, blocked, last_updated)
        VALUES 
            (%s, %s, %s, FALSE, FALSE, CURRENT_TIMESTAMP)
        ON CONFLICT (book_id, user_id)
        DO UPDATE SET predicted_rating = %s
        """, [title_id, USER_ID, prediction, prediction])

conn.close()
