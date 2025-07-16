# Adding a Lead to FollowUp Boss - Complete Workflow

Yes, you can add a lead with source, stage, and notes! Here are two approaches:

## Recommended Approach: Using create_event (Triggers Automations)

```python
# Step 1: Create the lead using an event (recommended by FollowUp Boss)
create_event(
    type="other",
    person={
        "name": "John Smith",
        "email": "john.smith@example.com",
        "phone": "+1234567890",
        "source": "Website Form",
        "stage": "New Lead"  # or "Hot Lead", "Qualified", etc.
    },
    note="Interested in 3-bedroom homes in downtown area. Budget: $500-700k. Pre-approved for financing.",
    source="Website Form"
)
```

This approach:
- ✅ Creates the contact
- ✅ Sets the source and stage
- ✅ Adds the initial note
- ✅ Triggers automations and workflows
- ✅ All in one API call

## Alternative Approach: Using Separate Calls

```python
# Step 1: Create the lead
response = create_person(
    name="John Smith",
    email="john.smith@example.com",
    phone="+1234567890",
    source="Website Form",
    stage="New Lead"
)

# Extract the person_id from response
person_id = response["person"]["id"]  # e.g., "12345"

# Step 2: Add a detailed note
create_note(
    person_id=person_id,
    body="Interested in 3-bedroom homes in downtown area. Budget: $500-700k. Pre-approved for financing.",
    is_html=False
)
```

## Available Stages (Default)

FollowUp Boss includes these built-in stages:
- **Lead** - New unqualified leads
- **Qualified** - Verified and qualified leads
- **Nurture** - Long-term follow-up
- **Active** - Actively working with
- **Under Contract** - In transaction
- **Closed** - Completed deals
- **Trash** - Dead/unqualified leads

## Example: Complete Lead Intake Workflow

```python
# 1. Add lead with initial categorization
create_event(
    type="other",
    person={
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1987654321",
        "source": "Zillow",
        "stage": "New Lead"
    },
    note="Zillow inquiry: Looking for investment properties",
    source="Zillow"
)

# 2. After initial contact, update stage and add follow-up
person_id = "12345"  # from previous response

update_person(
    person_id=person_id,
    stage="Qualified"
)

create_note(
    person_id=person_id,
    body="Spoke with Jane - investor looking for multi-family properties. Cash buyer. Send portfolio of duplex/triplex listings."
)

# 3. Create a follow-up task
create_task(
    description="Send investment property portfolio to Jane",
    person_id=person_id,
    due_date="2024-12-25T10:00:00Z"
)
```

## Source Options

Common source values:
- "Website Form"
- "Zillow"
- "Realtor.com"
- "Facebook"
- "Google Ads"
- "Referral"
- "Open House"
- "Phone Call"
- Custom values specific to your business

## Best Practices

1. **Use create_event for new leads** - It triggers automations
2. **Set meaningful sources** - Helps track ROI
3. **Use appropriate stages** - Helps with pipeline management
4. **Add detailed initial notes** - Provides context for follow-up
5. **Create tasks immediately** - Ensures timely follow-up

The current MCP server fully supports this workflow!