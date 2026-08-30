-- BigQuery views over the ledger (agent_logs.agent_events, fed by the native
-- Pub/Sub BigQuery subscription). Run once:  bq query --use_legacy_sql=false < infra/bq_views.sql

CREATE OR REPLACE VIEW `new-prompt-490003.agent_logs.events_v` AS
SELECT
  JSON_VALUE(data, '$.run_id')          AS run_id,
  JSON_VALUE(data, '$.event_type')      AS event_type,
  JSON_VALUE(data, '$.trigger_source')  AS trigger_source,
  JSON_VALUE(data, '$.agent')           AS agent,
  TIMESTAMP_MILLIS(CAST(JSON_VALUE(data, '$.ts_ms') AS INT64)) AS ts,
  data,
  publish_time
FROM `new-prompt-490003.agent_logs.agent_events`;

-- One row per run: when, how triggered, what it cost, what was refused.
CREATE OR REPLACE VIEW `new-prompt-490003.agent_logs.runs_v` AS
SELECT
  run_id,
  MIN(ts) AS started,
  MAX(ts) AS last_event,
  ANY_VALUE(trigger_source) AS trigger_source,
  COUNTIF(event_type = 'model_usage') AS model_calls,
  ROUND(SUM(IF(event_type = 'model_usage',
               CAST(JSON_VALUE(data, '$.cost_microcents') AS INT64), 0)) / 1e6, 4) AS cost_cents,
  COUNTIF(event_type = 'policy_denial') AS policy_denials,
  COUNTIF(event_type = 'action_dispatched') AS actions_dispatched,
  COUNTIF(event_type = 'action_executed') AS actions_executed
FROM `new-prompt-490003.agent_logs.events_v`
GROUP BY run_id;

-- Every refusal the policy engine ever wrote — the red-team beat lives here.
CREATE OR REPLACE VIEW `new-prompt-490003.agent_logs.denials_v` AS
SELECT run_id, ts,
  JSON_VALUE(data, '$.stage')  AS stage,
  JSON_VALUE(data, '$.rule')   AS rule,
  JSON_VALUE(data, '$.detail') AS detail
FROM `new-prompt-490003.agent_logs.events_v`
WHERE event_type = 'policy_denial'
ORDER BY ts DESC;

-- THE zero-private-egress proof (expected result: 0 rows, always):
-- every outbound model call is scanned against salted hashes of the family's
-- protected names; this view holds any call that matched or was blocked.
CREATE OR REPLACE VIEW `new-prompt-490003.agent_logs.egress_violations_v` AS
SELECT run_id, ts, event_type,
  CAST(JSON_VALUE(data, '$.matches') AS INT64) AS matches
FROM `new-prompt-490003.agent_logs.events_v`
WHERE event_type = 'egress_block'
   OR (event_type = 'egress_check'
       AND CAST(JSON_VALUE(data, '$.matches') AS INT64) > 0);

-- Where the local Gemma tier earns its keep: PII spans caught in-house.
CREATE OR REPLACE VIEW `new-prompt-490003.agent_logs.privacy_tier_v` AS
SELECT ts, run_id,
  JSON_VALUE(data, '$.privacy_tier') AS tier,
  CAST(JSON_VALUE(data, '$.model_spans') AS INT64) AS gemma_spans,
  CAST(JSON_VALUE(data, '$.map_hits') AS INT64) AS map_hits
FROM `new-prompt-490003.agent_logs.events_v`
WHERE event_type = 'school_mail_ingested'
ORDER BY ts DESC;
