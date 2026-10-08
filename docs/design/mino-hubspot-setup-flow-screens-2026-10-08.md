# Mino – Connect HubSpot setup flow (screen design)

*2026-10-08 · Companion to `mino-hubspot-discovery-migration-design-v0.3.md`*

**Interactive canvas:** https://claude.ai/artifact/6zG1mWtjNEAScwbNJYtd6p (private; share it from the page's Share menu)

**The flow:** Connect HubSpot → Mino learns → 7 questions → move the data → switch day

**Design system:** Plus Jakarta Sans. Colours: action #4B3FA8, accent #7B6FD8, background #F5F4FF, navy #1A1A2E, logo #9B93E0. Warning #B5530F, muted text #4F4C6B. The Admin Agent speaks as a chat bubble with the "M" avatar.

---

## Main flow

| # | Screen | Purpose | Key content |
|---|---|---|---|
| 1 | Where do you sell today? | Choose the source CRM | HubSpot, Salesforce, spreadsheet, or nothing |
| 2 | Create a read-only key | Get a HubSpot Service Key. No HubSpot app (D3). | Steps in HubSpot, the list of permissions to tick, a field to paste the key, and "Email the steps to my Super Admin" |
| 3 | Confirm the account | Make sure it is the right HubSpot account | Account name and ID, with a short snapshot of what is in it |
| 4 | Mino reads HubSpot | Discovery is running | Progress through pipelines, fields, users and history. Automations are inferred from behaviour (D8). |
| 5 | Question 1 of 7 | Admin Agent interview | The Company Memory findings shown as questions with a suggested answer. Target 7 questions, cap 12 (O11). |
| 6 | Setup summary | Review what Mino configured | Three columns: Set up / Left out by your choice / I'll ask you later. Buttons: "Move my data" (opens screen 7) and "Invite my team first". |
| 7 | Moving your data | Copy the data while HubSpot stays live | See the details below |
| 8 | Switch day | Cut over to Mino | See the details below |

## Error screens

| Screen | Trigger | What it offers |
|---|---|---|
| Waiting for a Super Admin | The user can't create a Service Key | The steps are emailed with a private link to paste the key (valid 7 days). Setup continues meanwhile: connect Gmail, invite the team. |
| Looks like the wrong account | The key works, but the account looks like a test or sandbox account | Reasons shown: no deals closed in the last 12 months, sandbox flag, company name mismatch. Buttons: paste a key from another account, or read it anyway. |
| Key not accepted / missing permissions | HTTP 401, or a 403 caused by missing scopes | Invalid key: the three usual causes (cut off, rotated, wrong kind of key). Missing scopes: the required and nice-to-have scopes, with the path to edit the same key. |

---

## Screen 7 · Moving your data

The Admin Agent explains that HubSpot keeps working and that changes arrive within 10 minutes.

**Header:** "Syncing with HubSpot · checked 3 min ago · every 10 min". This is delta polling (D7).

**Progress, one row per type of record** (counts from the test account):

| Record type | Count | Status |
|---|---|---|
| Companies | 30 | Done |
| Contacts | 62 | Done |
| Deals | 136 | Done |
| Emails | 122 | Done |
| Calls | 82 | In progress |
| Meetings | 52 | Queued |
| Notes | 121 | Queued |
| Attachments | – | Queued |

**Two inline data-quality decisions.** A default is selected for each.
- Contacts without a company: **create companies from the email domain** (O1), or leave them without a company.
- Deal owners not yet in Mino: **add them as pending users** (O2), or give their deals to the admin.

**Side panel**
- Until the switch, HubSpot is where people edit. Fields that come from HubSpot are read-only in Mino (O6).
- Rules are ready but switched off, so nobody gets tasks twice.
- The key is read-only and Mino never writes to HubSpot. Attachments are copied to Mino storage (O7).

**Call to action:** "Plan the switch", which opens screen 8.

## Screen 8 · Switch day

**Count check:** HubSpot count vs Mino count for each type of record, each row ticked. The rows are companies (showing the extra companies created from email domains), contacts, deals, activities, attachments and open pipeline value.

**Date choice:** Now / Monday 08:00 / Another day (within 30 days). The button reads "Switch to Mino now" or "Schedule the switch".

**At the switch**
1. A last copy of anything that changed in HubSpot.
2. Fields unlock.
3. Rules switch on.
4. The HubSpot key is deleted (D10).

**7-day undo window:** if the customer goes back, Mino provides a file of everything changed in Mino, ready to import into HubSpot.

---

## Open items for review (Oded)

1. **The 7-day undo.** The export-file behaviour is a design assumption and has not been decided. Should it be an export file, or something else?
2. **Placeholder values on screens 7 and 8:**
   - "9 companies created" and "3 deal owners" are illustrative examples;
   - the time-left estimate is illustrative;
   - the attachment count is shown as `[n]` and the pipeline value as `[$amount]`.
3. **O3 (how tasks migrate) is still open.** Tasks are not shown in the progress list yet.
4. **The "Invite my team first" path from screen 6** has no screen yet.
