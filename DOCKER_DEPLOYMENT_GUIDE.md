# Docker Deployment Guide for COBOL-to-Java Pipeline

## Overview
This guide walks you through building a custom Docker container with all dependencies (COBOL, Java, Python) pre-installed, pushing it to Google Container Registry, and submitting a Dataflow job that uses this container on all worker nodes.

## Why Docker?
- **Isolation**: Each Dataflow worker gets a consistent, reproducible environment
- **Dependencies**: Pre-installed GNU COBOL 4.0, OpenJDK 11, and Apache Beam
- **Reliability**: No startup surprises—the container is built once and used as-is on every worker
- **Scalability**: Scales to 10+ parallel jobs without environmental issues

## Prerequisites
On your local machine:
- ✓ Docker installed and running
- ✓ `gcloud` CLI configured with active authentication
- ✓ Google Cloud project: `cobol-to-java-converter-o`
- ✓ Permissions to: create Dataflow jobs, push to GCR, create GCS buckets

## Step-by-Step Deployment

### Option 1: Run the Automated Script (Recommended)
```bash
cd cobol-java-pipeline
chmod +x SUBMIT_TO_DATAFLOW.sh
./SUBMIT_TO_DATAFLOW.sh
```

This script handles:
1. GCP authentication
2. API enablement
3. Docker image build
4. GCR push
5. GCS bucket setup
6. Dataflow job submission

**Time estimate**: 5-10 minutes

### Option 2: Manual Steps

#### 1. Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project cobol-to-java-converter-o
```

#### 2. Enable Required APIs
```bash
gcloud services enable \
  dataflow.googleapis.com \
  container.googleapis.com \
  bigquery.googleapis.com \
  storage-component.googleapis.com
```

#### 3. Build Docker Image Locally
```bash
cd cobol-java-pipeline
docker build -t gcr.io/cobol-to-java-converter-o/dataflow-worker:latest .
```

Check it built successfully:
```bash
docker images | grep dataflow-worker
```

**What's included in the image:**
- Python 3.14
- OpenJDK 11 (Java)
- GNU COBOL 4.0
- Apache Beam[gcp] 2.76.0
- Git, curl, and build tools

#### 4. Push Image to Google Container Registry
```bash
docker push gcr.io/cobol-to-java-converter-o/dataflow-worker:latest
```

Verify:
```bash
gcloud container images describe gcr.io/cobol-to-java-converter-o/dataflow-worker
```

#### 5. Create GCS Buckets (if needed)
```bash
gsutil mb -c STANDARD -l us-central1 \
  gs://cobol-to-java-converter-o-dataflow-staging
gsutil mb -c STANDARD -l us-central1 \
  gs://cobol-to-java-converter-o-dataflow-temp
```

#### 6. Submit Dataflow Job
```bash
python3 dataflow_pipeline.py \
  --runner DataflowRunner \
  --project cobol-to-java-converter-o \
  --region us-central1 \
  --worker_zone us-central1-c \
  --staging_location gs://cobol-to-java-converter-o-dataflow-staging/staging \
  --temp_location gs://cobol-to-java-converter-o-dataflow-temp/temp \
  --num_workers 2 \
  --max_num_workers 4
```

## Monitoring the Job

### Check Job Status
```bash
gcloud dataflow jobs list --region us-central1
```

### View Full Job Details (Live)
```bash
# Replace JOB_ID with the ID from the list above
gcloud dataflow jobs show JOB_ID --region us-central1 --full
```

### Stream Logs
```bash
gcloud dataflow jobs show JOB_ID --region us-central1 --full | tail -100
```

### Query Results in BigQuery
```sql
SELECT 
  timestamp,
  job_id,
  validation_verdict,
  execution_time_seconds,
  status,
  error_message
FROM `cobol-to-java-converter-o.cobol_java_conversions.conversion_results`
ORDER BY timestamp DESC
LIMIT 10;
```

## What the Pipeline Does

1. **10 Parallel Jobs**: Each with different seed value (0-9)
2. **Stage 1 - GenerateEBCDICFn**: Creates 869-byte EBCDIC test data
3. **Stage 2 - RunCOBOLReaderFn**: Runs GNU COBOL reference implementation
4. **Stage 3 - RunJavaReaderFn**: Compiles and runs Java conversion
5. **Stage 4 - CompareOutputsFn**: Byte-for-byte comparison
6. **Stage 5 - WriteToBigQueryFn**: Formats results with proper types
7. **BigQuery Write**: Inserts results into conversion_results table

## Expected Results

**Success Indicators:**
- ✓ All 10 jobs complete within 5-10 minutes
- ✓ All validation_verdict values are 'PASS'
- ✓ execution_time_seconds shows actual elapsed time (typically 2-5 seconds per job)
- ✓ status is 'SUCCESS' for all rows
- ✓ error_message is NULL for all rows

**BigQuery Query for Verification:**
```sql
SELECT 
  COUNT(*) as total_jobs,
  COUNTIF(validation_verdict = 'PASS') as pass_count,
  COUNTIF(validation_verdict = 'FAIL') as fail_count,
  AVG(execution_time_seconds) as avg_time_seconds
FROM `cobol-to-java-converter-o.cobol_java_conversions.conversion_results`;
```

## Troubleshooting

### "Docker daemon not running"
- Start Docker Desktop on macOS/Windows or `sudo systemctl start docker` on Linux
- Verify with `docker ps`

### "Permission denied when pushing to GCR"
```bash
gcloud auth application-default login
gcloud auth configure-docker gcr.io
```

### "Worker pool quota exceeded"
- Reduce num_workers in the Dataflow command to 1 or 2
- Or request a quota increase in Google Cloud Console

### "Dataflow job shows UNKNOWN verdicts"
- Worker might be using old container image
- Delete job and resubmit with fresh image
- Verify image in job details: `gcloud dataflow jobs describe JOB_ID`

### "BigQuery dataset not found"
The pipeline auto-creates the dataset if needed. If there's an issue:
```bash
bq mk --dataset \
  --location=US \
  cobol-to-java-converter-o:cobol_java_conversions
```

## File Manifest

```
cobol-java-pipeline/
├── Dockerfile                          # Container definition
├── dataflow_pipeline.py               # Main pipeline (READY TO RUN)
├── 1_generate_ebcdic_weather.py       # Test data generator
├── 2_cobol_weather_reader.py          # COBOL executor
├── 4_compare_outputs.py               # Byte-for-byte validator
├── cobol_to_java_converter.py         # COBOL→Java converter
├── weather_reader.cob                 # Reference COBOL code
├── SUBMIT_TO_DATAFLOW.sh              # One-command submission script
└── DOCKER_DEPLOYMENT_GUIDE.md         # This file
```

## Key Changes Made for Docker Deployment

1. **Dockerfile Created**: Installs all dependencies in one container image
2. **Pipeline Updated**: Added `worker_harness_container_image` configuration pointing to the custom image
3. **Fixed Pipeline Logic**: 
   - WriteToBigQueryFn properly integrated in pipeline
   - Type casting for all BigQuery fields (float, int, str)
   - Correct TIMESTAMP formatting
   - Proper execution_time_seconds calculation

## Timeline to Interview

- **Now**: Set up Docker image (5-10 min)
- **+10 min**: Dataflow job submission
- **+5-10 min**: Job execution and results
- **Before 2pm**: Review results, prepare talking points

**Total time**: ~20-30 minutes

---

**Contact**: For issues, check /root/.ccr/README.md for proxy troubleshooting
