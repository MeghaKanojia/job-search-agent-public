# Databricks notebook source
# Cleans/dedupes bronze events into silver: normalizes whitespace/casing on
# title/company/location and drops exact duplicate payloads within the batch.

# COMMAND ----------

from pyspark.sql import functions as F

bronze = spark.table("bronze.raw_ingest_events")

parsed = bronze.select(
    "id",
    "source",
    "batch_id",
    "ingested_at",
    F.get_json_object("payload", "$.title").alias("title"),
    F.get_json_object("payload", "$.company").alias("company"),
    F.get_json_object("payload", "$.location").alias("location"),
    F.get_json_object("payload", "$.description").alias("description"),
    F.get_json_object("payload", "$.url").alias("url"),
)

cleaned = (
    parsed.withColumn("title_clean", F.trim(F.lower(F.col("title"))))
    .withColumn("company_clean", F.trim(F.lower(F.col("company"))))
    .withColumn("location_clean", F.trim(F.lower(F.col("location"))))
    .dropDuplicates(["title_clean", "company_clean", "location_clean"])
)

cleaned.write.format("delta").mode("overwrite").saveAsTable("silver.job_postings_clean")

print(f"Silver table refreshed with {cleaned.count()} deduplicated postings")
