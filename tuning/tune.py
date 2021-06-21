#!/usr/bin/python3
from surprise import SVD
from surprise import Dataset, Reader
from surprise.model_selection import GridSearchCV
from surprise import dump
import pickle
from customFolds import JumpStartKFolds

from sqlalchemy import create_engine
import pandas as pd

print("Connecting to db and loading data into memory...")
alchemyEngine = create_engine(
    'postgresql+psycopg2://postgres:@:5434/recsysdev')
conn = alchemyEngine.connect()

small_df = pd.read_sql("""
    SELECT r.user_id, r.book_id, r.rating
    FROM recsys_rating as r
    JOIN recsys_user as u ON u.id = r.user_id
    LEFT JOIN recsys_book_club_members as m ON m.user_id = u.id
    LEFT JOIN recsys_book_club as c ON c.id = m.book_club_id
    WHERE c.name = %s;
    """, conn, params=["The Somerville Sci-fi/Fantasy Book Club"])

large_df = pd.read_sql("""
    SELECT r.user_id, r.book_id, r.rating 
    FROM recsys_rating as r
    JOIN recsys_user as u ON u.id = r.user_id
    LEFT JOIN recsys_book_club_members as m ON m.user_id = u.id
    LEFT JOIN recsys_book_club as c ON c.id = m.book_club_id
    WHERE (
        c.name != %s
        OR c.name is NULL
    );
    """, conn, params=["The Somerville Sci-fi/Fantasy Book Club"])

df = pd.read_sql("""
    SELECT user_id, book_id, rating
    FROM recsys_rating
    WHERE rating is not NULL;
    """, conn)

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

    # 'lr_all': [ 0.005],

    'lr_pu': [0.0011, 0.0013,  0.0015],
    # 'lr_pu': [0.0009],

    'lr_bu': [0.0065, 0.007, 0.0075],
    # 'lr_bu': [0.006],

    'lr_bi': [0.0095, 0.0100, 0.0110],
    # 'lr_bi': [0.01],

    'lr_qi': [0.5, 0.8, 1.0],
    # 'lr_qi': [0.3],


    # 'reg_all': [0.4],

    # 'reg_bu': [0.025, 0.05, 0.075],
    'reg_bu': [0.025],

    # 'reg_bi': [0.15, 0.20, 0.25],
    'reg_bi': [0.20],
    
    # 'reg_pu': [0.30, 0.35, 0.40],
    'reg_pu': [0.30],

    # 'reg_qi': [0.30, 0.40, 0.7],
    'reg_qi': [0.30],

    
}


print("Gridsearch...")
gs = GridSearchCV(
    SVD, param_grid, measures=['rmse'], cv=3, n_jobs = -2)

gs.fit(data)

# best RMSE score
print(gs.best_score['rmse'])

# combination of parameters that gave the best RMSE score
print(gs.best_params['rmse'])

algo = gs.best_estimator['rmse']
algo.fit(data.build_full_trainset())


dump.dump('test.dump', algo=algo)
algo2 = dump.load('test.dump')[1]

uid = algo.trainset.to_inner_uid(557924)  # raw user id (as in the ratings file). They are **strings**!
iid = str(1475)  # raw item id (as in the ratings file). They are **strings**!

print(algo.predict(uid, iid, clip=False).est)
print(algo2.predict(uid, iid, clip=False).est)

all_ratings = [
    (
        algo.trainset.to_raw_iid(x), 
        title_dict.get(algo.trainset.to_raw_iid(x), 2858493), 
        algo.predict(uid, x, clip=False).est
    ) for x in algo.trainset.all_items()
]

r_df = pd.DataFrame(all_ratings)
r_df.sort_values(by=2, ascending=False, inplace=True)
