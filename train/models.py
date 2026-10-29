"""Tabular stackers. `soft` trains on the expert vote share (each row twice, weighted votes/5 and 1 - votes/5)."""

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class Tabular:
    def __init__(self, kind, soft=False, balanced=False):
        self.kind, self.soft, self.balanced = kind, soft, balanced

    def _new(self):
        if self.kind == "lr":
            return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=2000))
        return LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=20,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                              n_jobs=4, verbose=-1, random_state=0)

    def fit(self, X, rows):
        self.m = self._new()
        if self.soft:
            s = rows.votes.to_numpy() / 5
            X, y, w = np.vstack([X, X]), np.r_[np.ones(len(X)), np.zeros(len(X))], np.r_[s, 1 - s]
        else:
            y, w = rows.gold.to_numpy(), np.ones(len(X))
        if self.balanced:  # equal total weight per class, so scores keep one scale whatever the fold's prevalence
            w = w * np.where(y == 1, w.sum() / (2 * w[y == 1].sum()), w.sum() / (2 * w[y == 0].sum()))
        keep = w > 0
        self.m.fit(X[keep], y[keep], **{self._wkey(): w[keep]})
        return self

    def _wkey(self):
        return "logisticregression__sample_weight" if self.kind == "lr" else "sample_weight"

    def predict(self, X, rows):
        return self.m.predict_proba(X)[:, 1]
