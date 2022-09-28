# -*- coding: utf-8 -*-
"""main.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1itxkqOtq6jv6IbE7NCRtdgN3MqPFk-fL
"""

import gc
import os
#libraries preparetion
import warnings
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
# plot feature importance using built-in function
from numpy import loadtxt
#split the data
# from xgboostextension.scorer.metrics import ndcg
from sklearn.model_selection import GridSearchCV, GroupKFold, train_test_split
#Feature normalization
from sklearn.preprocessing import StandardScaler

import xgboost as XGB
#where the first column is the group ind, other columns are features
from run import load_data, preprocess_training_data
from xgboost import XGBClassifier, XGBRanker, plot_importance
from xgboost.sklearn import XGBClassifier

warnings.filterwarnings("ignore") #dont wanna se warning
sns.set(style="white",context="notebook",palette="muted")
pd.set_option('display.max_columns', None)


"""### Data preprocessing"""
base_dir = './data'
# base_dir = 'H:\\dataset\\2nd-assignment-dmt-2020'

#drop missing values more than threshold (60% by default)
def drop_columns_with_missing_data(
    df,
    threshold,
    ignore_values=[
        "visitor_hist_adr_usd",
        "visitor_hist_starrating",
        "srch_query_affinity_score",
        "prop_location_score2",
    ],
):
    columns_to_drop = []

    for i in range(df.shape[1]):
        length_df = len(df)
        column_names = df.columns.tolist()
        number_nans = sum(df.iloc[:, i].isnull())
        if number_nans / length_df > threshold:
            if column_names[i] not in ignore_values:
                columns_to_drop.append(column_names[i])

    print(
        "Dropping columns {} because they miss more than {} of data.".format(
            columns_to_drop, threshold
        )
    )

    df_reduced = df.drop(labels=columns_to_drop, axis=1)
    print("Dropped columns {}".format(columns_to_drop))
    return df_reduced


# split datetime to month hour dayofweek
def add_date_features(
    in_data, datetime_key="date_time", features=["month", "hour", "dayofweek"]
):
    dates = pd.to_datetime(in_data[datetime_key])
    for feature in features:
        if feature == "month":
            in_data["month"] = dates.dt.month
        elif feature == "dayofweek":
            in_data["dayofweek"] = dates.dt.dayofweek
        elif feature == "hour":
            in_data["hour"] = dates.dt.hour
    return in_data


#Build target column , booked = 5, clicked = 1, others= 0
def build_target_column(sum_val):
    if sum_val == 2:
        target = 5
    elif sum_val == 1:
        target = 1
    else:
        target = 0
    return target


# Feature importance selections
# load data
# training_set_only_metrics = ["click_bool", "booking_bool","target"]
# y = train["target"]
# X = train.drop(columns=training_set_only_metrics)
# fit model no training data
# model = XGBClassifier()
# model.fit(X,y)
# plot feature importance
# fig, ax = plt.subplots(1,1,figsize=(16,9))
# plot_importance(model,ax=ax)
# plt.show()


def normlaize_feature(series,log_it=False):
    '''normalize the data to standard normal distribution'''
    if log_it==True:
        arr = np.array(np.log2(series)).reshape(-1, 1)
    else:
        arr = np.array(series).reshape(-1, 1)
    norm_arr = StandardScaler().fit_transform(arr)
    return norm_arr.flatten()

def normalize_features(input_df, group_key, target_column, take_log10=False):
    # for numerical stability
    epsilon = 1e-4
    if take_log10:
        input_df[target_column] = np.log10(input_df[target_column] + epsilon)
    methods = ["mean", "std"]

    df = input_df.groupby(group_key).agg({target_column: methods})

    df.columns = df.columns.droplevel()
    col = {}
    for method in methods:
        col[method] = target_column + "_" + method

    df.rename(columns=col, inplace=True)
    df_merge = input_df.merge(df.reset_index(), on=group_key)
    df_merge[target_column + "_norm_by_" + group_key] = (
        df_merge[target_column] - df_merge[target_column + "_mean"]
    ) / df_merge[target_column + "_std"]
    df_merge = df_merge.drop(labels=[col["mean"], col["std"]], axis=1)

    gc.collect()
    return df_merge

#train["price_usd_log"] = np.log2(train["price_usd"])
#train = normalize_features(
#    train, group_key="prop_id", target_column="price_usd_log",take_log10=False
#) #TODO: TALK ABOUT THE LOG IS NOT WORKING
def load_data():

    fileName = os.path.join(base_dir, 'training_set_VU_DM.csv')
    fileName_test = os.path.join(base_dir, 'test_set_VU_DM.csv')

    train = pd.read_csv(fileName)
    test = pd.read_csv(fileName_test)
    test_srch_id = test['srch_id']
    test_prop_id = test['prop_id']


    train = drop_columns_with_missing_data(train,0.6)
    train.head()

    train = add_date_features(train)
    train.drop(labels=["date_time"], axis=1, inplace=True)
    train.head()

    target_column = "target"
    train[target_column] = train['click_bool'] + train['booking_bool']
    train[target_column] = train[target_column].map(lambda x: build_target_column(x))
    train.head()


    train = normalize_features(
        train, group_key="prop_id", target_column="price_usd",take_log10=False
    )
    train = normalize_features(
        train, group_key="srch_id", target_column="price_usd"
    )

    train = normalize_features(
        train, group_key="srch_destination_id", target_column="prop_location_score2"
    )

    train = normalize_features(
        train, group_key="prop_id", target_column="orig_destination_distance"
    )
    train = normalize_features(
        train, group_key="srch_id", target_column="orig_destination_distance"
    )

    # Feature importance ranking after engineering
    # load data
    training_set_only_metrics = ["click_bool", "booking_bool","target"]
    y = train["target"]
    X = train.drop(columns=training_set_only_metrics)
    # fit model no training data
    model = XGBClassifier()
    model.fit(X.iloc[:10000],y.iloc[:10000])
    # plot feature importance
    fig, ax = plt.subplots(1,1,figsize=(16,9))
    plot_importance(model,ax=ax)

    #select top 17 important features
    n = 17
    saved_features = [list(ax.get_yticklabels())[i].get_text() for i in range(n,len(list(ax.get_yticklabels())))]

    overlapped_features = ["prop_location_score2","price_usd","position", 'srch_id', 'prop_id']
    X = X[saved_features]
    overlapped_features = [f for f in overlapped_features if f in X.columns]
    X = X.drop(columns=overlapped_features)

    # Feature eng to test data
    test = drop_columns_with_missing_data(test,0.6)

    test = normalize_features(
        test, group_key="prop_id", target_column="price_usd",take_log10=False
    )
    test = normalize_features(
        test, group_key="srch_id", target_column="price_usd"
    )

    test = normalize_features(
        test, group_key="srch_destination_id", target_column="prop_location_score2"
    )

    test = normalize_features(
        test, group_key="prop_id", target_column="orig_destination_distance"
    )
    test = normalize_features(
        test, group_key="srch_id", target_column="orig_destination_distance"
    )

    test = add_date_features(test)
    test.drop(labels=["date_time"], axis=1, inplace=True)
    saved_features.remove("position")
    test = test[saved_features]
    overlapped_features = ["prop_location_score2","price_usd"]
    test = test.drop(columns=overlapped_features)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    #Final output
    catergorical_col = ["prop_id","srch_id","visitor_location_country_id","prop_country_id","srch_booking_window","srch_destination_id"]
    X = X #Training set
    y = y #Target series
    groups = train["srch_id"]
    test = test #Test data after feature engineering
    test = test.drop(labels=['srch_id', 'prop_id'], axis=1)
    print('finished the data processing')
    return X, y, groups, test, test_srch_id, test_prop_id

#NOTE: TODO: 
#Data not all normalized/standarized. 
#Target(label) column used 5 for booked prop, 1 for cliked
#Categorical_col could be used for LGBMRanker parameter
# "position" feature dropped
#Just try to get the first score

"""# Train and testing"""


def save(X, y, groups, test, test_srch_id, test_prop_id):
    X.to_pickle(os.path.join(base_dir, 'perfect_fX.pkl'), compression='gzip')
    y.to_pickle(os.path.join(base_dir, 'perfect_fyy.pkl'), compression='gzip')
    groups.to_pickle(os.path.join(base_dir, 'perfect_fgroups.pkl'), compression='gzip')
    test.to_pickle(os.path.join(base_dir, 'perfect_ftest.pkl'), compression='gzip')
    test_srch_id.to_pickle(os.path.join(base_dir, 'perfect_ftest_si.pkl'), compression='gzip')
    test_prop_id.to_pickle(os.path.join(base_dir, 'perfect_ftest_pi.pkl'), compression='gzip')



def groups2group(groups):
    return groups.value_counts(sort=False).sort_index()

def generate_configs(config):
    config_li = [{}]
    for k, v in config.items():
        new_config_li = []
        if(isinstance(v, list)):
            for conf in config_li:
                # config_li.remove(conf)
                for vv in v:
                    nc  =dict(conf)
                    nc[k] = vv
                    new_config_li.append(nc)
            config_li = new_config_li
        else:
            for conf in config_li:
                conf[k] = v
    return config_li

def run(X, y, groups, test, test_srch_id, test_prop_id):
    # gkf = GroupKFold(10)
    # print(len(X))
    # subsampled_inds = next(iter(gkf.split(X, y, groups)))[-1]
    # print(len(subsampled_inds))
    # X = X.iloc[subsampled_inds]
    # y = y.iloc[subsampled_inds]
    
    # groups = groups.iloc[subsampled_inds]
    gc.collect()
    # params = {'objective': 'rank:ndcg', 'n_estimators': 40, 'max_depth': 3, 'learning_rate': 0.1, 'subsample': 0.5,
    #           'early_stopping_rounds': [10, 5], 'seed': 7}
    params = {'objective': ['rank:pairwise', 'rank:ndcg'], 'n_estimators': 4000, 'max_depth': [3, 5, 10], 'learning_rate': 0.1, 'subsample': 0.5,
              'early_stopping_rounds': [100,], 'seed': 7}
    
    params_list = generate_configs(params)
    
    gkf = GroupKFold(5)
    best_param = None
    best_mean_ndcg = 0
    for param in params_list:
        val_metrics_li = []
        print(param)
        for train_inds, val_inds in gkf.split(X, y, groups):
            X_train, X_val = X.iloc[train_inds], X.iloc[val_inds]
            y_train, y_val = y.iloc[train_inds], y.iloc[val_inds]
            groups_train, groups_val = groups.iloc[train_inds], groups.iloc[val_inds]
            group_train = groups2group(groups_train)
            group_val = groups2group(groups_val)
            gc.collect()
            ranker = XGBRanker(**param)
            ranker.fit(X_train, y_train, group_train, verbose=True, eval_set=[
                    (X_train, y_train), (X_val, y_val)], eval_group=[group_train, group_val], eval_metric='ndcg@5-', early_stopping_rounds=param['early_stopping_rounds'])
            val_metrics_li.append(ranker.evals_result['eval_1']['ndcg@5-'][-1])
        mean_val = np.mean(val_metrics_li)
        if mean_val > best_mean_ndcg:
            best_mean_ndcg = mean_val
            best_param = param
        print('current best param:', best_param)
        print('current best val_ndcg:', best_mean_ndcg)
    

    # train the best config
    print('train the best config:')
    group = groups2group(groups)
    ranker = XGBRanker(**best_param)
    ranker.fit(X, y, group, verbose=True, eval_set=[
            (X, y)], eval_group=[group], eval_metric='ndcg@5-', early_stopping_rounds=param['early_stopping_rounds'])

    # predict
    predict(ranker, test, test_srch_id, test_prop_id)
    return best_param

def predict(model, X, srch_id, prop_id):
    predictions = model.predict(X)
    test_data_srch_id_prop_id = pd.concat([srch_id, prop_id], axis=1, sort=False)
    test_data_srch_id_prop_id["prediction"] = predictions
    test_data_srch_id_prop_id = test_data_srch_id_prop_id.sort_values(
        ["srch_id", "prediction"], ascending=True
    )
    print("Saving predictions into submission.csv")
    test_data_srch_id_prop_id[["srch_id", "prop_id"]].to_csv(
        os.path.join(base_dir, "submission.csv"), index=False
    )



def train_and_predict(X, y, groups, test, test_srch_id, test_prop_id):
    # params = {'objective': 'rank:ndcg', 'n_estimators': 1000, 'max_depth': 3, 'learning_rate': 0.1, 'subsample': 0.5,
    #           'early_stopping_rounds': 100, 'seed': 7, 'tree_method': 'gpu_hist'}
    # group = groups2group(groups)
    # ranker = XGBRanker(**params)
    # ranker.fit(X, y, group, verbose=True, eval_set=[
    #         (X, y)], eval_group=[group], eval_metric='ndcg@5-', early_stopping_rounds=100)
    import joblib
    # joblib.dump(ranker, 'xgb.pkl')
    ranker = joblib.load('xgb.pkl')

    predictions = ranker.predict(test)
    test_data_srch_id_prop_id = pd.concat(
        [test_srch_id, test_prop_id], axis=1, sort=False)
    test_data_srch_id_prop_id["prediction"] = predictions
    test_data_srch_id_prop_id = test_data_srch_id_prop_id.sort_values(
        ["srch_id", "prediction"], ascending=[True, False]
    )
    print("Saving predictions into submission-xgboost.csv")
    test_data_srch_id_prop_id[["srch_id", "prop_id"]].to_csv(
        os.path.join(base_dir, "submission-xgboost.csv"), index=False
    )


if __name__ == "__main__":
        
    # load train data
    LOAD = True
    if not LOAD:
        X, y, groups, test, test_srch_id, test_prop_id = load_data()
        print(set(X.columns)-set(test.columns))
        # X, y = preprocess_training_data(train_data)
        # yy = train_data['click_bool']+4*train_data['booking_bool']
        save(X, y, groups, test, test_srch_id, test_prop_id)
        print('finish caching data')
        # exit()
    else:
        X = pd.read_pickle(os.path.join(base_dir, 'perfect_fX.pkl'), compression='gzip')
        y= pd.read_pickle(os.path.join(base_dir, 'perfect_fyy.pkl'), compression='gzip')
        groups= pd.read_pickle(os.path.join(base_dir, 'perfect_fgroups.pkl'), compression='gzip')
        test= pd.read_pickle(os.path.join(base_dir, 'perfect_ftest.pkl'), compression='gzip')
        test_srch_id= pd.read_pickle(os.path.join(base_dir, 'perfect_ftest_si.pkl'), compression='gzip')
        test_prop_id= pd.read_pickle(os.path.join(base_dir, 'perfect_ftest_pi.pkl'), compression='gzip')
        print(np.unique(y))
        print('finish loading data')
        group = groups.value_counts(sort=False).sort_index()
        gc.collect()


    print(np.unique(y))

    train_and_predict(X, y, groups, test, test_srch_id, test_prop_id)

# groups = X['srch_id'].to_numpy()
# X.drop(columns=['srch_id'])
# X = X.to_numpy()
# yy = yy.to_numpy()
# print(X[:, 2])
# run(X, yy, groups)
