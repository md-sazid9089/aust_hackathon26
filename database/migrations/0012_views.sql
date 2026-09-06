-- 0012 views (security_invoker => RLS of the caller applies) + catch-up grants

CREATE OR REPLACE VIEW public.v_course_run_summary
WITH (security_invoker = true) AS
SELECT c.owner_id,
       c.id   AS course_id,
       c.code,
       c.title,
       ea.id  AS last_exam_audit_run_id,
       (SELECT count(*) FROM public.findings f WHERE f.run_id = ea.id AND f.status = 'open')::int AS exam_open_findings,
       (ea.summary ->> 'coverage_pct')::numeric AS exam_coverage_pct,
       la.id  AS last_attainment_run_id,
       (SELECT count(*) FILTER (WHERE ar.met) FROM public.attainment_results ar
         WHERE ar.run_id = la.id AND ar.target_kind = 'course_outcome')::int AS cos_met,
       (SELECT count(*) FROM public.attainment_results ar
         WHERE ar.run_id = la.id AND ar.target_kind = 'course_outcome')::int AS cos_total
FROM public.courses c
LEFT JOIN LATERAL (
  SELECT r.* FROM public.runs r
  WHERE r.course_id = c.id AND r.module = 'exam_audit' AND r.status IN ('completed','partial')
  ORDER BY r.finished_at DESC NULLS LAST LIMIT 1) ea ON true
LEFT JOIN LATERAL (
  SELECT r.* FROM public.runs r
  WHERE r.course_id = c.id AND r.module = 'attainment' AND r.status IN ('completed','partial')
  ORDER BY r.finished_at DESC NULLS LAST LIMIT 1) la ON true
WHERE c.deleted_at IS NULL;

CREATE OR REPLACE VIEW public.v_admin_department_attainment
WITH (security_invoker = true) AS
SELECT p.email       AS owner_email,
       c.code        AS course_code,
       r.id          AS run_id,
       r.finished_at,
       (SELECT count(*) FILTER (WHERE ar.met) FROM public.attainment_results ar
         WHERE ar.run_id = r.id AND ar.target_kind = 'course_outcome')::int AS cos_met,
       (SELECT count(*) FROM public.attainment_results ar
         WHERE ar.run_id = r.id AND ar.target_kind = 'course_outcome')::int AS cos_total,
       w.target_code AS weakest_co_code,
       w.attained_pct AS weakest_pct
FROM public.runs r
JOIN public.profiles p ON p.id = r.owner_id
JOIN public.courses  c ON c.id = r.course_id
LEFT JOIN LATERAL (
  SELECT ar.target_code, ar.attained_pct
  FROM public.attainment_results ar
  WHERE ar.run_id = r.id AND ar.target_kind = 'course_outcome' AND NOT ar.met
  ORDER BY ar.attained_pct ASC LIMIT 1) w ON true
WHERE r.module = 'attainment' AND r.status IN ('completed','partial');

CREATE OR REPLACE VIEW public.v_admin_exam_audit_summary
WITH (security_invoker = true) AS
SELECT p.email  AS owner_email,
       c.code   AS course_code,
       r.id     AS run_id,
       r.finished_at,
       (r.summary ->> 'coverage_pct')::numeric AS coverage_pct,
       COALESCE(jsonb_array_length(r.summary -> 'duplicates'), 0) AS duplicates,
       (SELECT count(*) FROM public.findings f WHERE f.run_id = r.id AND f.status = 'open')::int AS open_findings
FROM public.runs r
JOIN public.profiles p ON p.id = r.owner_id
JOIN public.courses  c ON c.id = r.course_id
WHERE r.module = 'exam_audit' AND r.status IN ('completed','partial');

CREATE OR REPLACE VIEW public.v_admin_usage
WITH (security_invoker = true) AS
SELECT u.user_id,
       p.email,
       date_trunc('day', u.created_at)::date AS day,
       count(*)::int                          AS calls,
       COALESCE(sum(u.tokens_in), 0)::bigint  AS tokens_in,
       COALESCE(sum(u.tokens_out), 0)::bigint AS tokens_out,
       COALESCE(sum(u.cost_usd), 0)::numeric(12,6) AS cost_usd,
       count(*) FILTER (WHERE u.status = 'failed')::int AS failures
FROM public.usage_logs u
LEFT JOIN public.profiles p ON p.id = u.user_id
GROUP BY u.user_id, p.email, date_trunc('day', u.created_at);

-- Catch-up grants for objects created before default privileges took effect
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_backend;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_backend;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_backend;
