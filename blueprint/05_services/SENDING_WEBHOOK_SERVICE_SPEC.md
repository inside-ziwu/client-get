# Sending and Webhook Service Spec

## 1. Sending plan start

`start_sending_plan(plan_id)` must:

1. Lock plan row `FOR UPDATE`.
2. Verify status in draft/scheduled/paused as applicable.
3. Verify domain is `verification_status='verified'`.
4. Verify steps exist and step 1 is valid.
5. Compute or verify locked recipients.
6. Exclude blacklisted, unsubscribed, bounced, incomplete company, no valid email.
7. Create `sending_plan_recipients` if not locked.
8. Create `sequence_enrollments` with `next_step_due_at`.
9. Set plan running/started_at.

## 2. Due email worker

```text
query active enrollments due now
for each enrollment:
  find current step
  evaluate condition from previous events
  try insert email_send_locks(enrollment_id, step_id)
  reserve domain quota
  render template
  insert emails(status='queued')
  call EngageLab
  update emails sent/failed
  update enrollment current_step/next_step_due_at/completed
```

## 3. Domain quota reserve

Reserve must be atomic:

```sql
UPDATE domain_daily_usage
SET reserved_count = reserved_count + :n
WHERE domain_id = :domain_id
  AND usage_date = current_date
  AND reserved_count + :n <= daily_limit
RETURNING *;
```

If no row exists, create it from `domain_warmup_status.daily_limit` inside transaction.

## 4. Webhook transaction

For each EngageLab event:

```text
BEGIN
  insert email_events, on conflict do nothing
  if duplicate: COMMIT return 204
  locate email by engagelab_message_id
  update emails status/timestamps
  if replied/bounced/unsubscribed:
    update sequence_enrollments terminal status
    update tenant_contacts status
  if delivered/opened/clicked:
    update emails only
COMMIT
```

## 5. Reply handling

If EngageLab supports inbound reply payload, store:

- reply_message_id
- reply_from_email
- reply_subject
- reply_body_text
- reply_received_at

If not supported, keep reply UI placeholder and do not fake reply content.
