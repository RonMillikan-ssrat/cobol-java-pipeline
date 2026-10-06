#!/bin/bash
# Complete script to build Docker image, push to GCR, and submit Dataflow job
# Run this on your local machine with Docker and gcloud access

set -e

PROJECT_ID="cobol-to-java-converter-o"
REGION="us-central1"
ZONE="us-central1-c"
IMAGE_NAME="dataflow-worker"
GCR_IMAGE="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest"
PIPELINE_SCRIPT="dataflow_pipeline.py"

echo "=========================================="
echo "COBOL-to-Java Pipeline Dataflow Submission"
echo "=========================================="
echo ""

# Step 1: Authenticate with GCP
echo "Step 1: Authenticating with Google Cloud..."
gcloud auth login
gcloud config set project $PROJECT_ID
echo "✓ Authentication complete"
echo ""

# Step 2: Enable required APIs
echo "Step 2: Enabling required Google Cloud APIs..."
gcloud services enable dataflow.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable storage-component.googleapis.com
gcloud services enable bigquery.googleapis.com
echo "✓ APIs enabled"
echo ""

# Step 3: Build Docker image
echo "Step 3: Building Docker image..."
docker build -t $GCR_IMAGE .
if [ $? -eq 0 ]; then
  echo "✓ Docker image built successfully"
else
  echo "✗ Docker build failed"
  exit 1
fi
echo ""

# Step 4: Push to Google Container Registry
echo "Step 4: Pushing Docker image to Google Container Registry..."
echo "Image: $GCR_IMAGE"
docker push $GCR_IMAGE
if [ $? -eq 0 ]; then
  echo "✓ Image pushed to GCR successfully"
else
  echo "✗ Push to GCR failed - check authentication"
  exit 1
fi
echo ""

# Step 5: Create GCS buckets if they don't exist
echo "Step 5: Setting up Google Cloud Storage buckets..."
STAGING_BUCKET="gs://${PROJECT_ID}-dataflow-staging"
TEMP_BUCKET="gs://${PROJECT_ID}-dataflow-temp"

gsutil mb -c STANDARD -l $REGION $STAGING_BUCKET 2>/dev/null || echo "Staging bucket already exists"
gsutil mb -c STANDARD -l $REGION $TEMP_BUCKET 2>/dev/null || echo "Temp bucket already exists"
echo "✓ GCS buckets ready"
echo ""

# Step 6: Submit to Dataflow
echo "Step 6: Submitting pipeline to Google Cloud Dataflow..."
echo "This will start 10 parallel jobs across Dataflow workers"
echo ""

python3 $PIPELINE_SCRIPT \
  --runner DataflowRunner \
  --project $PROJECT_ID \
  --region $REGION \
  --worker_zone $ZONE \
  --staging_location $STAGING_BUCKET/staging \
  --temp_location $TEMP_BUCKET/temp \
  --num_workers 2 \
  --max_num_workers 4 \
  --machine_type n1-standard-4

if [ $? -eq 0 ]; then
  echo ""
  echo "✓ Pipeline submitted successfully!"
  echo ""
  echo "Next steps:"
  echo "1. Monitor progress: gcloud dataflow jobs list --region $REGION"
  echo "2. View live job: gcloud dataflow jobs show JOB_ID --region $REGION --full"
  echo "3. Query results when complete:"
  echo "   SELECT * FROM \`${PROJECT_ID}.cobol_java_conversions.conversion_results\`"
  echo "   ORDER BY timestamp DESC LIMIT 10;"
else
  echo ""
  echo "✗ Pipeline submission failed"
  exit 1
fi
