-- DROP VIEW IF EXISTS jira.vw_issue_links_raw CASCADE;
-- DROP VIEW IF EXISTS jira.vw_issue_fields CASCADE;
-- DROP VIEW IF EXISTS jira.vw_issue_links CASCADE;
-- DROP VIEW IF EXISTS jira.vw_issue_label CASCADE;

SET SEARCH_PATH = 'jira';

CREATE OR REPLACE VIEW jira.vw_issue_links_raw AS
SELECT issue_key, watermark, JSON_ARRAY_ELEMENTS((raw -> 'fields' -> 'issuelinks')::json) AS link
FROM jira.jira_issue;

CREATE OR REPLACE VIEW jira.vw_issue_links AS
SELECT jl.issue_key                              AS issue_key,
       jl.link -> 'type' ->> 'name'              AS link_type,
       ji.issue_key                              AS linked_issue_key,
       ji.raw -> 'fields' -> 'status' ->> 'name' AS linked_issue_status,
       ji.raw -> 'fields' ->> 'summary'          AS linked_issue_summary
FROM jira.vw_issue_links_raw jl
         JOIN jira.jira_issue ji ON jl.link -> 'outwardIssue' ->> 'key' = ji.issue_key;

CREATE OR REPLACE VIEW jira.vw_issue_label AS
SELECT q.issue_key,
       issue_label::VARCHAR(50) AS label
FROM (SELECT issue_key,
             JSON_ARRAY_ELEMENTS_TEXT((raw -> 'fields' ->> 'labels')::json) AS issue_label
      FROM jira.jira_issue) AS q;

CREATE OR REPLACE VIEW jira.vw_issue_fields AS
SELECT issue_key,
       fields.key   AS field,
       fields.value AS value
FROM jira.jira_issue i,
     JSONB_EACH((raw -> 'fields')::jsonb) AS fields;

CREATE OR REPLACE VIEW jira.vw_issue_component AS
SELECT q.issue_key,
       (q.component ->> 'name')::VARCHAR(20)    AS name,
       (q.component ->> 'description')::VARCHAR AS description,
       (q.component ->> 'id')::INTEGER          AS component_id,
       q.component                              AS raw
FROM (SELECT issue_key,
             JSON_ARRAY_ELEMENTS((raw -> 'fields' ->> 'components')::json) AS component
      FROM jira.jira_issue) AS q;
