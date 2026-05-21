## Scoring Framework

The qualification model uses 5 factors summing to 100 points:
- Segment Fit (20 pts): Is the company in a priority vertical for this product?
- Buyer Fit (20 pts): Is this person a decision maker, champion, or influencer?
- Pain Fit (25 pts): Is there explicit or implied production/workflow pain?
- Workflow Fit (20 pts): Does the signal engagement quality confirm a relevant workflow?
- Commercial Fit (15 pts): Does company size, funding, and momentum suggest budget exists?

Decision thresholds:
- score >= qualified_threshold → "qualified"
- score < disqualified_threshold → "disqualified"
- disqualified_threshold <= score < qualified_threshold → "review"

The score MUST equal the sum of all five sub-scores.
Each sub-score must not exceed its maximum (segment ≤ 20, buyer ≤ 20, pain ≤ 25, workflow ≤ 20, commercial ≤ 15).
