### Multi-Agent QA & Iterative Verification

After completing the requested implementation, do not consider the task finished yet.

1. Spawn multiple independent QA/testing sub-agents with different responsibilities (e.g., functional testing, edge cases, security, UX, integration, regression, and end-to-end testing) as required for this.
2. Each sub-agent must independently inspect and test the implementation, identify bugs, missing requirements, regressions, and potential improvements, and provide a score out of 10 with evidence.
3. Aggregate the findings and determine an overall quality score.
4. The main implementation agent must analyze all feedback, fix the identified issues, and re-run the QA agents.
5. Repeat this implementation → independent verification → feedback → improvement loop until the system achieves at least 9/10, or all agents agree that no meaningful improvements remain.
6. Do not inflate scores. Testing must be evidence-based, and agents should explicitly distinguish between verified, partially verified, and unverified behavior.
7. At the end, provide:

   * Final score /10
   * Tests performed
   * Issues found and fixed
   * Remaining known limitations
   * Confirmation that the final implementation was re-tested after the fixes.

Important: QA agents must remain independent from the implementation agent's reasoning and should actively try to break the system rather than simply confirming that it works.