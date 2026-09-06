# Databricks notebook source
# Reads unprocessed raw_ingest_events from Postgres (Neon) into a Delta bronze table.
# Runs on the Databricks Workflow's own native schedule -- never triggered externally
# by GitHub Actions (see README for why: Free Edition's external-trigger support via
# REST API is unconfirmed, so the two systems are fully decoupled).

# COMMAND ----------

pg_url = dbutils.secrets.get(scope="job-search-agent", key="database-url")

raw_df = (
    spark.read.format("jdbc")
    .option("url", f"jdbc:{pg_url}")
    .option("dbtable", "(SELECT * FROM raw_ingest_events WHERE processed_at IS NULL) t")
    .load()
)

raw_df.write.format("delta").mode("append").saveAsTable("bronze.raw_ingest_events")

print(f"Landed {raw_df.count()} unprocessed events into bronze.raw_ingest_events")
