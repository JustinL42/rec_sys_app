#!/usr/bin/python3
from surprise import SVD
from surprise import Dataset, Reader
from surprise.model_selection import GridSearchCV
from surprise import dump
import pickle
from customFolds import JumpStartKFolds

from sqlalchemy import create_engine
import pandas as pd

REAL_BOOK_CLUB_ID = 8

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
    SVD, param_grid, measures=['rmse'], cv=3, n_jobs = -2)

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


dump.dump('test.dump', algo=algo)
algo2 = dump.load('test.dump')[1]

uid = algo.trainset.to_inner_uid(557924)
iid = str(  )

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


try:
    rmse_to_beat = pickle.load(open("rmse_to_beat.pickle", "rb"))
except FileNotFoundError: 
    rmse_to_beat = 99999

if best_rmse <= rmse_to_beat:
    print("A new record")
    print(r_df.head(15))
    dump.dump("bestAlgo.pickle", algo=gs.best_estimator['rmse'])

    pickle.dump(best_rmse, open("rmse_to_beat.pickle", "wb"))
    logFile = open("rmse_records.txt", "a")
    logFile.write("\n{}\nRMSE: {}\n{}\n".format(
            gs.algo_class.__name__, gs.best_params['rmse'], best_rmse
        )
    )
    logFile.close()
