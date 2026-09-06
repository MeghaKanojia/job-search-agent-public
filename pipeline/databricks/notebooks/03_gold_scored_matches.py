# Databricks notebook source
# Scores silver postings against the user's skill profile (rule-based keyword
# overlap -- same logic as backend/app/services/matching.py, kept in sync
# manually until enough labeled outcomes exist to justify an MLflow model) and
# writes scores back to Postgres job_postings so the dashboard never queries
# Databricks on the request path.

# COMMAND ----------

from pyspark.sql import functions as F

pg_url = dbutils.secrets.get(scope="job-search-agent", key="database-url")

silver = spark.table("silver.job_postings_clean")

skills_df = (
    spark.read.format("jdbc")
    .option("url", f"jdbc:{pg_url}")
    .option("dbtable", "(SELECT skill_name FROM skill_profile_items WHERE is_active = TRUE) t")
    .load()
)
skill_names = [r["skill_name"].lower() for r in skills_df.collect()]

# Keep in sync with backend/app/services/matching.py's STRONG_MATCH_SKILL_COUNT --
# dividing by the full skill-profile size made even a strong match (5-6 overlapping
# skills) score near zero, since no single posting mentions most of a 70-item profile.
STRONG_MATCH_SKILL_COUNT = 5

# COMMAND ----------


def score_row(description: str) -> float:
    if not description or not skill_names:
        return 0.0
    text = description.lower()
    matched = sum(1 for s in skill_names if s in text)
    return round(min(matched / STRONG_MATCH_SKILL_COUNT, 1.0), 4)


score_udf = F.udf(score_row, "double")

scored = silver.withColumn("keyword_match_score", score_udf(F.col("description")))

scored.write.format("delta").mode("overwrite").saveAsTable("gold.scored_job_postings")

# Write scores back to the operational Postgres table the dashboard actually reads from.
(
    scored.select(
        F.col("title").alias("title"),
        F.col("company").alias("company"),
        "keyword_match_score",
    )
    .write.format("jdbc")
    .option("url", f"jdbc:{pg_url}")
    .option("dbtable", "gold_scores_staging")
    .mode("overwrite")
    .save()
)

print("Gold scoring complete; see docs/SETUP.md for the staging-table merge step "
      "(a MERGE INTO job_postings ... from gold_scores_staging, run via a follow-up "
      "SQL task in the same Workflow).")
