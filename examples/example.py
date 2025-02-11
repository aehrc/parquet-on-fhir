import duckdb

duckdb.read_parquet("ExplanationOfBenefit.parquet")

duckdb.sql("SELECT id FROM 'ExplanationOfBenefit.parquet'").show()
