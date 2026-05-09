from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import os
import json
import difflib


# Load model and metadata
model_path = "fraud_job_model.pkl"
meta_path = "fraud_job_meta.pkl"

if not os.path.exists(model_path) or not os.path.exists(meta_path):
    raise FileNotFoundError(f"Model files not found. Please ensure {model_path} and {meta_path} exist.")

model = joblib.load(model_path)
meta = joblib.load(meta_path)
cat_cols = meta["cat_cols"]
num_cols = meta["num_cols"]

app = Flask(__name__)

import json

# Load red-flag patterns from JSON
RED_FLAG_GROUPS = {}

red_flags_path = "red_flags.json"
if os.path.exists(red_flags_path):
    with open(red_flags_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        auto_flags = data.get("auto_red_flags", [])
        RED_FLAG_GROUPS["auto"] = auto_flags
else:
    # Fallback default patterns if JSON missing
    RED_FLAG_GROUPS = {
        "money": [
            "earn per week", "daily payment", "high payout",
            "instant payment", "commission based", "unlimited income"
        ],
        "no_process": [
            "no interview", "no experience needed", "100% guarantee",
            "instant approval", "join immediately"
        ],
        "too_good": [
            "work from home and earn", "make money from home",
            "urgent requirement", "limited seats only"
        ]
    }


# Personal data leak terms
PERSONAL_DATA_PATTERNS = [
    "aadhaar", "aadhar", "pan card", "passport", "bank account",
    "ifsc", "cvv", "social security", "id card", "driver's license"
]

# Employer credibility config
TRUSTED_COMPANIES = []
trusted_path = "trusted_companies.json"
if os.path.exists(trusted_path):
    try:
        with open(trusted_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            TRUSTED_COMPANIES = data.get("trusted_companies", [])
    except Exception as e:
        print("Error loading trusted_companies.json:", e)


def compute_employer_credibility(company_name: str,
                                 company_profile: str,
                                 has_company_logo: int,
                                 industry: str,
                                 telecommuting: int) -> int:
    """
    Compute a simple 0-100 employer credibility score using
    offline signals + hooks for future online checks.
    """

    score = 50  # base

    name_clean = (company_name or "").strip()
    profile_len = len(company_profile or "")
    industry_clean = (industry or "").strip()

    # 1. Company logo is a strong positive signal
    if has_company_logo:
        score += 15
    else:
        score -= 10

    # 2. Reasonable company profile length
    if profile_len > 300:
        score += 15
    elif profile_len < 50:
        score -= 10

    # 3. Industry known vs Unknown/Other
    if industry_clean.lower() not in ["unknown", "", "other"]:
        score += 5
    else:
        score -= 5

    # 4. Telecommuting with no logo is a bit suspicious
    if telecommuting == 1 and not has_company_logo:
        score -= 10

    # 5. Fuzzy match against trusted companies list (offline)
    if name_clean and TRUSTED_COMPANIES:
        best_match = difflib.get_close_matches(name_clean, TRUSTED_COMPANIES, n=1, cutoff=0.7)
        if best_match:
            score += 15



    # clip to [0, 100]
    score = max(0, min(100, score))
    return int(score)



@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    try:
        # Read form fields
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        requirements = request.form.get("requirements", "").strip()
        company_profile = request.form.get("company_profile", "").strip()
        benefits = request.form.get("benefits", "").strip()

        employment_type = request.form.get("employment_type", "Unknown").strip()
        required_experience = request.form.get("required_experience", "Unknown").strip()
        required_education = request.form.get("required_education", "Unknown").strip()
        industry = request.form.get("industry", "Unknown").strip()
        function = request.form.get("function", "Unknown").strip()

        has_company_logo = int(request.form.get("has_company_logo", "0"))
        has_questions = int(request.form.get("has_questions", "0"))
        telecommuting = int(request.form.get("telecommuting", "0"))

        # Combine text
        text_all = " ".join([
            title,
            description,
            requirements,
            company_profile,
            benefits
        ]).strip()

        # Create length-based features
        desc_len = len(description)
        req_len = len(requirements)
        profile_len = len(company_profile)
        benefits_len = len(benefits)

        # Basic validation
        words = text_all.split()
        if len(words) < 5 or len(text_all) < 30:
            return render_template("index.html", 
                error="Input too short or low-information. Please provide a proper job description.")

        # Build dataframe for model
        X_new = pd.DataFrame([{
            "text_all": text_all,
            "employment_type": employment_type,
            "required_experience": required_experience,
            "required_education": required_education,
            "industry": industry,
            "function": function,
            "has_company_logo": has_company_logo,
            "has_questions": has_questions,
            "telecommuting": telecommuting,
            "desc_len": desc_len,
            "req_len": req_len,
            "profile_len": profile_len,
            "benefits_len": benefits_len
        }])

        # Red flag phrase scanning
        text_lower = text_all.lower()
        red_flags_found = []

        for group, phrases in RED_FLAG_GROUPS.items():
            for phrase in phrases:
                if phrase in text_lower:
                    red_flags_found.append(phrase)

        red_flags_clean = sorted(set(red_flags_found))
        red_flags_display = ", ".join(red_flags_clean) if red_flags_clean else "None detected"


        # Personal data risk
        personal_hits = [p for p in PERSONAL_DATA_PATTERNS if p in text_lower]

        if personal_hits:
            personal_risk = f"High (mentions: {', '.join(personal_hits)})"
        else:
            personal_risk = "Low"

        # Model confidence & risk level
        score = float(model.decision_function(X_new)[0])

        high_thr = 0.8
        low_thr = -0.8

        if score > high_thr:
            base_pred = 1
            risk_level = "High – Strong Fraud Indicators"
        elif score < low_thr:
            base_pred = 0
            risk_level = "Low – Likely Genuine"
        else:
            base_pred = int(model.predict(X_new)[0])
            risk_level = "Medium – Suspicious / Low Confidence"

        # Semantic fraud score (0-100) based on SVM margin
        # Clamp score to a reasonable range, e.g., [-5, 5]
        max_abs_margin = 5.0
        clipped = max(min(score, max_abs_margin), -max_abs_margin)
        # Map [-max_abs_margin, max_abs_margin] -> [0, 100]
        fraud_semantic_score = (clipped + max_abs_margin) / (2 * max_abs_margin) * 100
        fraud_semantic_score = round(fraud_semantic_score, 1)


        # Force Fraud Classification if Personal Data Requested
        if personal_hits:
            base_pred = 1
            risk_level = "High – This posting requests sensitive personal information"

        # Make sure label is consistent with final base_pred
        label = "Fraudulent" if base_pred == 1 else "Real"

        # Employer credibility score (0-100)
        employer_name = title
        employer_credibility = compute_employer_credibility(
            company_name=employer_name,
            company_profile=company_profile,
            has_company_logo=has_company_logo,
            industry=industry,
            telecommuting=telecommuting
        )

        return render_template("result.html",
                               label=label,
                               prediction=int(base_pred),
                               red_flags=red_flags_display,
                               personal_risk=personal_risk,
                               risk_level=risk_level,
                               fraud_semantic_score=fraud_semantic_score,
                               employer_credibility=employer_credibility)



    except Exception as e:
        print(f"Error in predict: {str(e)}")
        return render_template("index.html", 
                             error="An error occurred while processing your request. Please try again.")


# API Route
@app.route("/predict_api", methods=["POST"])
def predict_api():

    data = request.get_json(force=True)

    title = data.get("title", "")
    description = data.get("description", "")
    requirements = data.get("requirements", "")
    company_profile = data.get("company_profile", "")
    benefits = data.get("benefits", "")

    employment_type = data.get("employment_type", "Unknown")
    required_experience = data.get("required_experience", "Unknown")
    required_education = data.get("required_education", "Unknown")
    industry = data.get("industry", "Unknown")
    function = data.get("function", "Unknown")

    has_company_logo = int(data.get("has_company_logo", 1))
    has_questions = int(data.get("has_questions", 0))
    telecommuting = int(data.get("telecommuting", 0))

    text_all = " ".join([
        title,
        description,
        requirements,
        company_profile,
        benefits
    ]).strip()

    desc_len = len(description)
    req_len = len(requirements)
    profile_len = len(company_profile)
    benefits_len = len(benefits)

    X_new = pd.DataFrame([{
        "text_all": text_all,
        "employment_type": employment_type,
        "required_experience": required_experience,
        "required_education": required_education,
        "industry": industry,
        "function": function,
        "has_company_logo": has_company_logo,
        "has_questions": has_questions,
        "telecommuting": telecommuting,
        "desc_len": desc_len,
        "req_len": req_len,
        "profile_len": profile_len,
        "benefits_len": benefits_len
    }])

    score = float(model.decision_function(X_new)[0])

    if score > 0.8:
        risk_level = "High"
    elif score < -0.8:
        risk_level = "Low"
    else:
        risk_level = "Medium"

    return jsonify({
        "prediction": int(model.predict(X_new)[0]),
        "risk_level": risk_level
    })


if __name__ == "__main__":
    app.run(debug=True)
