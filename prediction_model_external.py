from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import median_absolute_error
from sklearn.metrics import mean_squared_error
import math
import numpy as np

class PredictionModelExternal:
    """ External (Scikit-Learn) Machine Learning Model - function that outputs prediction based on input to the model """
    def __init__(self, prediction_config, prediction_data, prediction_utils):
        self.prediction_config = prediction_config
        self.prediction_data = prediction_data
        self.prediction_utils = prediction_utils
        self.training_columns = prediction_data.get_training_columns()
        self.target_column = self.prediction_config.TARGET_COLUMN
        self.knn = None

    def generate_knn_model(self, qty_neighbors, algorithm, distance_type):
        self.knn = KNeighborsRegressor(n_neighbors=qty_neighbors, algorithm=algorithm, p=distance_type)

    def process_hyperparameter_fixed(self):
        """
        Step 1: Create instance of K-Nearest-Neighbors Machine Learning Model class where p=2 is Euclidean Distance
        Step 2: Fit the Model using by specifying data for K-Nearest-Neighbor Model to use:
            - X as Training data (i.e. DataFrame "feature" Columns from Training data)
            - y as Target values (i.e. DataFrame's Target Column)

            X argument of `fit` function is matrix-like object, containing cols of interest from Training set (to make predictions)
            y argument of `fit` function is list-like object, containing just TARGET_COLUMN, `price`.

            X and y are passed into `fit` method of Scikit-Learn.
                Warning: DO NOT pass in data containing the following else Error occurs:
                    - Missing values
                    - Non-numerical values

        Step 3: Scikit-Learn's `predict` function called to make predictions on cols of test_df.
            Returns NumPy array of predicted "price" TARGET_COLUMN values

        Step 4: Calculate MAE, MSE, and RMSE float values for each individual Target, where least loss "best" values are 0
        """
        print("Training features include: %r" % (self.training_columns) )

        self.generate_knn_model(self.prediction_config.HYPERPARAMETER_FIXED, 'brute', 2)

        _temp_training_part = self.prediction_data.training_part
        X = _temp_training_part[self.training_columns]
        y = _temp_training_part[self.target_column]

        self.knn.fit(X, y)

        _temp_testing_part = self.prediction_data.testing_part
        predictions = self.knn.predict(_temp_testing_part[self.training_columns])

        print("Predictions using Scikit-Learn: %r" % (predictions) )

        mae = median_absolute_error(_temp_testing_part[self.target_column], predictions)
        mse = mean_squared_error(_temp_testing_part[self.target_column], predictions, multioutput='raw_values')
        rmse = math.sqrt(mse)

        print("MAE: %r" % (mae) )
        print("MSE: %r" % (mse[0]) )
        print("RMSE: %r" % (rmse) )

        mae_rmse_ratio_prefix = mae / rmse
        print("MAE to RMSE Ratio: %.2f:1" % (mae_rmse_ratio_prefix) )
        for index, training_model_feature_name in enumerate(self.training_columns):
            self.prediction_utils.plot(training_model_feature_name, _temp_testing_part)

    def process_hyperparameter_optimisation(self):
        """ Hyperparameter 'k' Optimisation """
        print("Hyperparameter k Optimisation in progress...")

        hyperparam_range = self.prediction_config.HYPERPARAMETER_RANGE

        training_column_names = self.training_columns
        feature_combos = self.prediction_utils.generate_combinations_of_features(training_column_names)

        feature_combos_rmse_for_hyperparams = dict()

        if self.prediction_config.K_FOLD_CROSS_VALIDATION == False:
            _temp_training_part = self.prediction_data.training_part
            _temp_testing_part = self.prediction_data.testing_part

            for idx1, feature_combo in enumerate(feature_combos):
                feature_combo_key = '__'.join(feature_combo)
                feature_combos_rmse_for_hyperparams[feature_combo_key] = list()
                for idx2, qty_neighbors in enumerate(hyperparam_range):
                    knn = KNeighborsRegressor(n_neighbors=qty_neighbors, algorithm="brute", p=2)
                    X = _temp_training_part[list(feature_combo)]
                    y = _temp_training_part[self.target_column]
                    knn.fit(X, y)
                    predictions = knn.predict(_temp_testing_part[list(feature_combo)])
                    mse = mean_squared_error(_temp_testing_part[self.target_column], predictions, multioutput='raw_values')
                    rmse = math.sqrt(mse[0])
                    feature_combos_rmse_for_hyperparams[feature_combo_key].append(rmse)
        # Combining K-Fold Cross Validation with Hyperparameter 'k' Optimisation
        else:
            fold_ids = list(range(1, self.prediction_config.K_FOLDS + 1))
            df = self.prediction_data.df_listings

            for idx1, feature_combo in enumerate(feature_combos):
                feature_combo_key = '__'.join(feature_combo)
                feature_combos_rmse_for_hyperparams[feature_combo_key] = list()
                for idx2, qty_neighbors in enumerate(hyperparam_range):

                    fold_rmses = []
                    for fold in fold_ids:
                        # Train
                        model = KNeighborsRegressor(n_neighbors=qty_neighbors, algorithm="brute", p=2)
                        train_part = df[df["fold"] != fold]
                        test_part = df[df["fold"] == fold]
                        X = train_part[list(feature_combo)]
                        y = train_part[self.target_column]
                        model.fit(X, y)
                        # Predict
                        labels = model.predict(test_part[list(feature_combo)])
                        test_part["predicted_price"] = labels
                        mse = mean_squared_error(test_part[self.target_column], test_part["predicted_price"])
                        rmse = mse**(1/2)
                        fold_rmses.append(rmse)
                    # print("Fold RMSEs %r: " % (fold_rmses))
                    avg_rmse = np.mean(fold_rmses)
                    # print("Average RMSE: %r" % (avg_rmse))
                    feature_combos_rmse_for_hyperparams[feature_combo_key].append(avg_rmse)

        feature_combos_lowest_rmse_for_hyperparams = dict()

        for key, value in feature_combos_rmse_for_hyperparams.items():
            # Initiate element with lowest RMSE as first element unless find a lower element at subsequent index
            feature_combos_lowest_rmse_for_hyperparams[key] = dict()
            feature_combos_lowest_rmse_for_hyperparams[key]["min_rmse"] = feature_combos_rmse_for_hyperparams[key][0]
            for k, rmse in enumerate(feature_combos_rmse_for_hyperparams[key]):
                if rmse < feature_combos_lowest_rmse_for_hyperparams[key]["min_rmse"]:
                    feature_combos_lowest_rmse_for_hyperparams[key]["min_rmse"] = rmse
                    feature_combos_lowest_rmse_for_hyperparams[key]["k"] = k + 1

        # Find best combination of hyperparameter k and features

        # Initiate element with lowest RMSE as first element unless find a lower element at subsequent index
        name_of_first_key = list(feature_combos_lowest_rmse_for_hyperparams.keys())[0]
        feature_combo_name_with_lowest_rmse = name_of_first_key
        lowest_rmse = feature_combos_lowest_rmse_for_hyperparams[name_of_first_key]["min_rmse"]
        k_value_of_lowest_rmse = feature_combos_lowest_rmse_for_hyperparams[name_of_first_key]["k"]

        for feature_key, dict_value in feature_combos_lowest_rmse_for_hyperparams.items():
            if dict_value["min_rmse"] < lowest_rmse:
                feature_combo_name_with_lowest_rmse = feature_key
                lowest_rmse = dict_value["min_rmse"]
                k_value_of_lowest_rmse = dict_value["k"]
        print("Feature combo %r has lowest RMSE of %r with 'k' of %r (optimum) using %r K-Folds for (Cross Validation was %r)" % (feature_combo_name_with_lowest_rmse, lowest_rmse, k_value_of_lowest_rmse, self.prediction_config.K_FOLDS, self.prediction_config.K_FOLD_CROSS_VALIDATION) )

        self.prediction_utils.plot_hyperparams(feature_combos_lowest_rmse_for_hyperparams)

def run(prediction_config, prediction_data, prediction_utils):
    """
    Scikit-Learn Workflow depending on config chosen
    """
    prediction_model_external = PredictionModelExternal(prediction_config, prediction_data, prediction_utils)

    if prediction_config.HYPERPARAMETER_OPTIMISATION == True:
        prediction_model_external.process_hyperparameter_optimisation()
    else:
        prediction_model_external.process_hyperparameter_fixed()
