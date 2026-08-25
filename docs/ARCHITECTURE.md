# Architecture Description

The AI Revenue Recovery Agent pipeline operates as follows:

1. **Detection Agent**: Rule-based component that scans the dataset for revenue-at-risk events (failed payments, abandoned checkouts, overdue invoices).
2. **Diagnosis Agent**: Uses the Gemini LLM to classify the root cause of the identified issue.
3. **Decision Engine**: Maps the diagnosed root cause to a bounded intervention strategy (e.g., retry now, retry later, send reminder, escalate to support, offer discount).
4. **Execution Layer**: Simulates/executes Razorpay retry or reminder actions based on the decision.
5. **Guardrails**: Implements safety checks (max retry caps, stopping rules, compliance checks).
6. **Audit Trail**: Logs every decision and outcome for transparency and improvement.
7. **Streamlit Dashboard**: Provides a visual interface to monitor recovery metrics and system health.
