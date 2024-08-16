rec_sys_app - the source code for BookClub.Guide
==========================

![](https://user-images.githubusercontent.com/3272143/212499736-26e8f1d8-7730-4c27-9076-c9275e57d8f7.png)

[BookClub.Guide](https://bookclub.guide) is a recommendation system Django web app where readers and book clubs can get recommendations on books they might enjoy. Using a database derived from the [Internet Speculative Fiction Database's](http://www.isfdb.org) regularly-updated snapshots, users can give ratings to nearly any sci-fi/fantasy book available in English. These ratings are are used to help find recommendations for the user, as well as for other users with similar taste.

Some of the motivations for this project include:

* Most large recommendation systems for books such as Goodreads are owned by Amazon or other companies that sell books. They are incentivized to recommend books that you are likely to buy, which may not be the same thing as books you are likely to enjoy.
* Book clubs need to choose books that will appeal to the group overall, rather than just some members. A feature of this project (still under development) would suggest books based on the average the members' predicted ratings. 

The algorithm used to generate recommendations is a [collaborative filtering](https://en.wikipedia.org/wiki/Collaborative_filtering), [matrix factorization](https://en.wikipedia.org/wiki/Matrix_factorization_(recommender_systems)) model. Specifically, this is the [SVD algorithm](https://surprise.readthedocs.io/en/stable/matrix_factorization.html#surprise.prediction_algorithms.matrix_factorization.SVD) from the [Surprise](http://surpriselib.com/) python package, with some customizations. 

The [Book Crossing](https://web.archive.org/web/20230319134511/http://www2.informatik.uni-freiburg.de/~cziegler/BX/) ratings data set was used jump start the model-tuning. The data isn't an ideal fit for this application for a number of reasons. Because of this, the algorithm's evaluation function was modified so that only the accuracy of predictions for the site's real users (not Book Crossings ratings) was used to guide the tuning of the model.

## Installation

See [INSTALLATION.md](INSTALLATION.md).
