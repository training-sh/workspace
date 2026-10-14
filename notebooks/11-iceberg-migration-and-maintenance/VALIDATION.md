# Validation record

All seven notebooks completed twice inside Kubernetes, with a fresh Python kernel and a separate data namespace for every execution.
Every execution verified that Spark work ran on a separate executor. All core code cells executed; no cell errors were permitted or recorded.
All connection override variables were unset for both complete passes. The notebooks used their printed Kubernetes Service DNS defaults with the existing credential environment. No manifest change was needed.

| Notebook | Pass 1 | Pass 2 | Checks per pass |
|---|---:|---:|---:|
| 01_hive_sources_and_migration_design.ipynb | PASS (102.8 s) | PASS (88.71 s) | 18 / 18 |
| 02_shallow_and_in_place_migration.ipynb | PASS (69.63 s) | PASS (61.82 s) | 9 / 9 |
| 03_snapshot_migration_and_validation.ipynb | PASS (69.71 s) | PASS (71.26 s) | 12 / 12 |
| 04_hybrid_migration_and_cutover.ipynb | PASS (71.03 s) | PASS (74.23 s) | 12 / 12 |
| 05_late_arriving_data_and_replay.ipynb | PASS (70.01 s) | PASS (70.08 s) | 10 / 10 |
| 06_hidden_partitions_and_partition_evolution.ipynb | PASS (64.69 s) | PASS (62.19 s) | 9 / 9 |
| 07_branches_tags_and_table_maintenance.ipynb | PASS (101.85 s) | PASS (102.21 s) | 22 / 22 |

The checks cover complete row reconciliation, all four source layouts, original-file reuse, snapshot isolation, malformed-type quarantine, phased cutover, replay safety, partition evolution, branch promotion and rollback, compaction, retention and scoped orphan cleanup. Notebook 01 additionally verifies a HiveCatalog Iceberg table on HDFS and an ordinary Parquet write/read through Hadoop S3A, independently of Polaris S3FileIO.

Each notebook contains its Spark builder and catalog configuration directly, without importing a lesson helper. SQL operations are separated into cells with short comments and visible assertions.

The [machine-readable record](assets/validation/acceptance.json) includes source SHA-256 hashes, execution IDs, cell counts and results. The raw hashes match the delivered notebook sources and validator; portable hashes also identify the same content after Git normalizes line endings.

Source notebooks have clean outputs for classroom use. Executed copies were retained as operational test evidence outside the lesson folder. The classroom exercises and assignments are extensions to the tested core workflow.

Each notebook has an SVG source and an embedded PNG. All seven PNGs were rendered from their SVGs, checked for valid dimensions and relative links, and reviewed for text clipping.

To repeat the two passes in the course Kubernetes workbench:

```bash
python assets/validate_notebooks.py --passes 2 --output /tmp/migration-validation
```
