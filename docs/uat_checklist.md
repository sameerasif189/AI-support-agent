# UAT Checklist

- Verify `/health` endpoint returns `ok`.
- Validate web channel response for top 10 FAQ intents.
- Validate ERP lookup flow for invoice/order queries.
- Validate sensitive request (`hack`, `delete account`) triggers human handoff.
- Confirm WhatsApp webhook receives and returns valid payload.
- Confirm Slack webhook receives event payload and returns response text.
- Validate budget metrics endpoint updates after chat calls.
- Test ticket creation path for low confidence responses.
- Confirm all responses stay within short-answer policy.
- Check logs include channel, intent class, and estimated response cost.
