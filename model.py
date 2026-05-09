import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report
from sklearn.feature_selection import chi2

from imblearn.over_sampling import RandomOverSampler

import joblib
import numpy as np
import json


DATA_PATH = "fake_job_postings.csv"
MODEL_PATH = "fraud_job_model.pkl"
META_PATH = "fraud_job_meta.pkl"
RED_FLAGS_PATH = "red_flags.json"


def load_data(path: str) -> pd.DataFrame:
    """Load the fake job posting dataset."""
    df = pd.read_csv(path)

    # Drop columns that are mostly useless or IDs
    drop_cols = []
    for col in ["job_id", "salary_range", "department", "location"]:
        if col in df.columns:
            drop_cols.append(col)

    if drop_cols:
        df = df.drop(columns=drop_cols)

    return df


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning + feature engineering on the dataframe."""

    # Define column groups (based on the dataset schema)
    text_cols = ["title", "description", "requirements", "company_profile", "benefits"]

    cat_cols = [
        "employment_type",
        "required_experience",
        "required_education",
        "industry",
        "function",
    ]

    num_cols = ["has_company_logo", "has_questions", "telecommuting"]

    # Handle missing values
    # Text: replace NaN with empty string
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")
        else:

            df[col] = ""

    # Categorical: replace NaN with "Unknown"
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
        else:
            df[col] = "Unknown"


    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    # Combine text fields into a single feature
    df["text_all"] = (
        df["title"]
        + " "
        + df["description"]
        + " "
        + df["requirements"]
        + " "
        + df["company_profile"]
        + " "
        + df["benefits"]
    )

    # Length-based features
    df["desc_len"] = df["description"].str.len()
    df["req_len"] = df["requirements"].str.len()
    df["profile_len"] = df["company_profile"].str.len()
    df["benefits_len"] = df["benefits"].str.len()

    return df


def build_pipeline(cat_cols, num_cols) -> Pipeline:
    """Create the ColumnTransformer + LinearSVC pipeline."""

    preprocessor = ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(stop_words="english", max_features=10000), "text_all"),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), cat_cols),
            ("numeric", "passthrough", num_cols),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", LinearSVC()),
        ]
    )

    return model


def generate_red_flag_patterns(df: pd.DataFrame,
                               output_path: str = RED_FLAGS_PATH,
                               top_n: int = 50) -> None:
    """
    Automatically mine red-flag n-grams that are strongly associated
    with fraudulent postings, and save them to a JSON file.

    This will be used by the Flask app instead of hardcoded keyword lists.
    """
    if "text_all" not in df.columns or "fraudulent" not in df.columns:
        print("Cannot generate red flags: 'text_all' or 'fraudulent' column missing.")
        return

    print("Generating red-flag patterns from dataset...")

    X_text = df["text_all"]
    y = df["fraudulent"]

    # Vectorize with unigrams + bigrams
    vectorizer = CountVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=5
    )
    X_vec = vectorizer.fit_transform(X_text)

    # chi2 to find features associated with fraud class (1)
    chi2_scores, _ = chi2(X_vec, y)
    feature_names = vectorizer.get_feature_names_out()

    # Pick top-N ngrams with highest chi2 scores
    indices = np.argsort(chi2_scores)[::-1][:top_n]
    top_terms = [feature_names[i] for i in indices]

    red_flags_dict = {
        "auto_red_flags": top_terms
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(red_flags_dict, f, indent=2, ensure_ascii=False)

    print(f"Saved top {len(top_terms)} red-flag patterns to {output_path}")


def main():
    print("Loading data...")
    df = load_data(DATA_PATH)

    print("Preprocessing dataframe...")
    df = preprocess_dataframe(df)

    
    cat_cols = [
        "employment_type",
        "required_experience",
        "required_education",
        "industry",
        "function",
    ]

    num_cols = [
        "has_company_logo",
        "has_questions",
        "telecommuting",
        "desc_len",
        "req_len",
        "profile_len",
        "benefits_len",
    ]

    # Features & target
    X = df[["text_all"] + cat_cols + num_cols]
    y = df["fraudulent"]

    print("Train-test split...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print("Applying RandomOverSampler on training data...")
    ros = RandomOverSampler(random_state=42)
    X_train_res, y_train_res = ros.fit_resample(X_train, y_train)

    print("Building pipeline...")
    model = build_pipeline(cat_cols, num_cols)

    print("Training model...")
    model.fit(X_train_res, y_train_res)

    print("Evaluating on test set...")
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    print(f"Saving model to {MODEL_PATH} ...")
    joblib.dump(model, MODEL_PATH)

    print(f"Saving metadata to {META_PATH} ...")
    joblib.dump({"cat_cols": cat_cols, "num_cols": num_cols}, META_PATH)

    # Generate red-flag patterns JSON for Flask app
    generate_red_flag_patterns(df, RED_FLAGS_PATH, top_n=50)

    print("Done.")


if __name__ == "__main__":
    main()
