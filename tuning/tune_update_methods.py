import os, sys
import pickle

from sqlalchemy import create_engine
import pandas as pd
from surprise import Dataset, Reader
from surprise.model_selection import GridSearchCV

from customSurpriseClasses import JumpStartKFolds, DefaultlessSVD

path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
import django
django.setup()
from recsys.models import SVDModel, Book_Club


def tune_svd_model():
	pass

def update_all_recs():
	pass

def tune_update_all_recs():
	tune_svd_model()
	update_all_recs()

def update_one_users_recs(id):
	pass