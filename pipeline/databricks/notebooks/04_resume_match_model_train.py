# Databricks notebook source
# Weekly task: once enough labeled outcomes exist (applications with a final
# status of applied/interview/offer/rejected), train a simple classifier on
# TF-IDF overlap features and log it to MLflow for TRACKING ONLY.
#
# Free Edition likely can't serve a live model endpoint (unconfirmed but probable,
# same as historical Community Edition behavior) -- so inference stays inside this
# notebook / the rule-based scorer in 03_gold_scored_matches.py, not a served API.

# COMMAND ----------

import mlflow
from pyspark.sql import functions as F

pg_url = dbutils.secrets.get(scope="job-search-agent", key="database-url")

labeled = (
    spark.read.format("jdbc")
    .option("url", f"jdbc:{pg_url}")
    .option(
        "dbtable",
        "(SELECT a.status, jp.description_clean, jp.keyword_match_score "
        "FROM applications a JOIN job_postings jp ON jp.id = a.job_posting_id "
        "WHERE a.status IN ('applied','interview','offer','rejected')) t",
    )
    .load()
)

MIN_LABELED_ROWS = 30
count = labeled.count()

# COMMAND ----------

if count < MIN_LABELED_ROWS:
    print(f"Only {count} labeled outcomes so far (need {MIN_LABELED_ROWS}+) -- skipping training this run.")
else:
    with mlflow.start_run(run_name="resume_match_v1"):
        pdf = labeled.toPandas()
        pdf["positive"] = pdf["status"].isin(["interview", "offer"]).astype(int)

        # Placeholder baseline: correlation between the existing rule-based score
        # and actual positive outcomes -- gives a real signal on whether the v1
        # keyword scorer is doing better than chance before investing in a real model.
        correlation = pdf["keyword_match_score"].corr(pdf["positive"])

        mlflow.log_metric("labeled_rows", count)
        mlflow.log_metric("score_outcome_correlation", correlation or 0.0)
        print(f"Logged baseline correlation={correlation} on {count} labeled rows to MLflow.")
