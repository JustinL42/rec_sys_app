from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from itertools import chain
from math import ceil, floor
import numpy as np
from surprise import SVD
from surprise.utils import get_rng
from surprise.model_selection import KFold


class DefaultlessSVD(SVD):

    def default_prediction(self):
        return None


# The following method (JumpStartKFolds) is a modification of the KFolds
# method from the Surprise python package by Nicholas Hug. It is being 
# used here under the terms of the BSD 3-Clause license. The original 
# source code can be found at https://github.com/NicolasHug/Surprise.
# Per the terms of the BSD 3-Clause License, Surprise's original 
# copyright notice, list of conditions, and disclaimer are retained here:

# Copyright (c) 2016, Nicolas Hug All rights reserved.

# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are
# met:

# 1) Redistributions of source code must retain the above copyright 
#    notice, this list of conditions and the following disclaimer.

# 2) Redistributions in binary form must reproduce the above copyright 
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# 3) Neither the name of the copyright holder nor the names of its 
#    contributors may be used to endorse or promote products derived 
#    from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR 
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT 
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


class JumpStartKFolds(KFold):
    """Custom k-folds that allows the use of a larger data set to 
    jump start predictions on a smaller data set. Only the accuracy of 
    predictions for the smaller data set is used in training. The entire
    larger data set is always used in the training set.
    """

    def __init__(
        self, large_data=None, n_splits=5, random_state=None, shuffle=True):
        if large_data == None:
            raise ValueError('Must provide large_data parameter '
                            'for JumpStartKFolds')

        self.large_data = large_data
        super().__init__(
            n_splits=n_splits, random_state=random_state, shuffle=shuffle)


    def split(self, small_data):
        """docstring
        """
        if small_data.reader.rating_scale != \
            self.large_data.reader.rating_scale:

            raise ValueError('Rating scales of large and small data '
                            'sets must match')


        if self.n_splits > len(small_data.raw_ratings) or self.n_splits < 2:
            raise ValueError('Incorrect value for n_splits={0}. '
                             'Must be >=2 and less than the number '
                             'of ratings in small dataset.'.format(
                                len(data.raw_ratings)))

        small_indices = np.arange(len(small_data.raw_ratings))
        large_indices = np.arange(len(self.large_data.raw_ratings))

        if self.shuffle:
            get_rng(self.random_state).shuffle(small_indices)
            get_rng(self.random_state).shuffle(large_indices)

        large_raw_ratings = [self.large_data.raw_ratings[i] for i in large_indices]

        start, stop = 0, 0
        for fold_i in range(self.n_splits):
            start = stop
            stop += len(small_indices) // self.n_splits
            if fold_i < len(small_indices) % self.n_splits:
                stop += 1

            raw_testset = [small_data.raw_ratings[i] for i in \
                chain(small_indices[:start], small_indices[stop:])]
            raw_trainset = [small_data.raw_ratings[i] for i in \
                small_indices[start:stop]]
            raw_trainset += large_raw_ratings

            trainset = small_data.construct_trainset(raw_trainset)
            testset = small_data.construct_testset(raw_testset)

            yield trainset, testset