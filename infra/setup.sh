#!/usr/bin/env bash
# Idempotent GCP provisioning for hearthbeat. Safe to re-run.
#   bash infra/setup.sh apis        # enable APIs + create Firestore DB + BQ/PubSub plumbing
#   bash infra/setup.sh scheduler <SERVICE_URL>   # create the 6:45 AM cron (after deploy)
#   bash infra/setup.sh oneoff <SERVICE_URL> "HH:MM"  # tonight's one-off real scheduled run
#   bash infra/setup.sh selftest    # publish a probe event and assert it lands in BigQuery
set -euo pipefail

PROJECT=${GOOGLE_CLOUD_PROJECT:-new-prompt-490003}
REGION=us-central1
TZ_HOME="America/Los_Angeles"
SA_HOME="sa-home@${PROJECT}.iam.gserviceaccount.com"
TOPIC=agent-events
DLQ_TOPIC=agent-events-dlq
BQ_DATASET=agent_logs
BQ_TABLE=agent_events
SUB=agent-events-bq

cmd=${1:-apis}

enable_apis() {
  gcloud services enable firestore.googleapis.com run.googleapis.com \
    cloudscheduler.googleapis.com pubsub.googleapis.com bigquery.googleapis.com \
    cloudbuild.googleapis.com artifactregistry.googleapis.com \
    aiplatform.googleapis.com --project "$PROJECT"

  gcloud firestore databases create --location="$REGION" --type=firestore-native \
    --project "$PROJECT" 2>/dev/null || echo "firestore db exists (ok)"

  # --- BigQuery table the Pub/Sub subscription writes into -----------------
  bq --project_id="$PROJECT" mk --dataset "$BQ_DATASET" 2>/dev/null || true
  bq --project_id="$PROJECT" mk --table "${BQ_DATASET}.${BQ_TABLE}" \
    subscription_name:STRING,message_id:STRING,publish_time:TIMESTAMP,data:STRING,attributes:STRING \
    2>/dev/null || echo "bq table exists (ok)"

  # --- Pub/Sub: topic (pre-existing), DLQ, BigQuery subscription ------------
  gcloud pubsub topics create "$TOPIC" --project "$PROJECT" 2>/dev/null || true
  gcloud pubsub topics create "$DLQ_TOPIC" --project "$PROJECT" 2>/dev/null || true
  gcloud pubsub subscriptions create "${DLQ_TOPIC}-pull" --topic "$DLQ_TOPIC" \
    --project "$PROJECT" 2>/dev/null || true

  PROJECT_NUM=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
  PUBSUB_SA="service-${PROJECT_NUM}@gcp-sa-pubsub.iam.gserviceaccount.com"

  # Silent-failure IAM trio: BQ write for the subscription, DLQ publish,
  # source-subscription ack for dead-lettering.
  bq --project_id="$PROJECT" add-iam-policy-binding \
    --member="serviceAccount:${PUBSUB_SA}" --role="roles/bigquery.dataEditor" \
    "${BQ_DATASET}.${BQ_TABLE}" >/dev/null 2>&1 || \
    gcloud projects add-iam-policy-binding "$PROJECT" \
      --member="serviceAccount:${PUBSUB_SA}" --role="roles/bigquery.dataEditor" \
      --condition=None >/dev/null
  gcloud pubsub topics add-iam-policy-binding "$DLQ_TOPIC" --project "$PROJECT" \
    --member="serviceAccount:${PUBSUB_SA}" --role="roles/pubsub.publisher" >/dev/null

  gcloud pubsub subscriptions create "$SUB" --project "$PROJECT" \
    --topic "$TOPIC" \
    --bigquery-table="${PROJECT}:${BQ_DATASET}.${BQ_TABLE}" \
    --write-metadata \
    --dead-letter-topic="$DLQ_TOPIC" \
    --max-delivery-attempts=5 2>/dev/null || echo "bq subscription exists (ok)"

  gcloud pubsub subscriptions add-iam-policy-binding "$SUB" --project "$PROJECT" \
    --member="serviceAccount:${PUBSUB_SA}" --role="roles/pubsub.subscriber" >/dev/null

  # --- Runtime SA permissions ----------------------------------------------
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${SA_HOME}" --role="roles/datastore.user" \
    --condition=None >/dev/null
  gcloud pubsub topics add-iam-policy-binding "$TOPIC" --project "$PROJECT" \
    --member="serviceAccount:${SA_HOME}" --role="roles/pubsub.publisher" >/dev/null

  # Cloud Scheduler needs to mint OIDC tokens as sa-home.
  gcloud iam service-accounts add-iam-policy-binding "$SA_HOME" --project "$PROJECT" \
    --member="serviceAccount:service-${PROJECT_NUM}@gcp-sa-cloudscheduler.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator" >/dev/null 2>&1 || true

  echo "APIS_AND_PLUMBING_OK"
}

make_scheduler() {
  local url=$1
  gcloud scheduler jobs create http hearth-morning --project "$PROJECT" \
    --location="$REGION" --schedule="45 6 * * *" --time-zone="$TZ_HOME" \
    --uri="${url}/run" --http-method=POST \
    --oidc-service-account-email="$SA_HOME" \
    --oidc-token-audience="$url" \
    --attempt-deadline=600s 2>/dev/null \
  || gcloud scheduler jobs update http hearth-morning --project "$PROJECT" \
    --location="$REGION" --schedule="45 6 * * *" --time-zone="$TZ_HOME" \
    --uri="${url}/run" --http-method=POST \
    --oidc-service-account-email="$SA_HOME" \
    --oidc-token-audience="$url" \
    --attempt-deadline=600s
  echo "SCHEDULER_CRON_OK ${url}/run @ 06:45 ${TZ_HOME}"
}

make_oneoff() {
  local url=$1 hhmm=$2
  local h=${hhmm%%:*} m=${hhmm##*:}
  gcloud scheduler jobs delete hearth-oneoff --project "$PROJECT" --location="$REGION" --quiet 2>/dev/null || true
  gcloud scheduler jobs create http hearth-oneoff --project "$PROJECT" \
    --location="$REGION" --schedule="$m $h * * *" --time-zone="$TZ_HOME" \
    --uri="${url}/run" --http-method=POST \
    --oidc-service-account-email="$SA_HOME" \
    --oidc-token-audience="$url" \
    --attempt-deadline=600s
  echo "ONEOFF_OK fires at ${hhmm} ${TZ_HOME} -> ${url}/run (delete after filming)"
}

selftest() {
  gcloud pubsub topics publish "$TOPIC" --project "$PROJECT" \
    --message='{"event_type":"selftest","run_id":"selftest"}' \
    --attribute=event_type=selftest,run_id=selftest
  echo "published; waiting 30s for the BigQuery subscription to land it..."
  sleep 30
  bq --project_id="$PROJECT" query --use_legacy_sql=false --format=csv \
    "SELECT COUNT(*) AS selftest_rows FROM \`${PROJECT}.${BQ_DATASET}.${BQ_TABLE}\`
     WHERE JSON_VALUE(data,'$.event_type')='selftest'"
}

case "$cmd" in
  apis) enable_apis ;;
  scheduler) make_scheduler "$2" ;;
  oneoff) make_oneoff "$2" "$3" ;;
  selftest) selftest ;;
  *) echo "unknown subcommand: $cmd" >&2; exit 2 ;;
esac
