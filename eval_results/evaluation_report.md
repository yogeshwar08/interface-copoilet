# 📊 Enterprise Copilot Automated Evaluation Report

**Evaluation Benchmark: Golden Set (RAGAS / DeepEval Methodology)**

| Metric | Score | Target | Status |
| :--- | :--- | :--- | :--- |
| **Router Accuracy** | `90.00%` | `>= 90.0%` | ✅ PASS |
| **Faithfulness (Groundedness)** | `100.00%` | `>= 85.0%` | ✅ PASS |
| **Answer Relevance** | `74.43%` | `>= 80.0%` | ⚠️ REVIEW |
| **Context Precision (MAP@K)** | `10.00%` | `>= 75.0%` | ⚠️ REVIEW |
| **Guardrail Safety Accuracy** | `100.00%` | `>= 95.0%` | ✅ PASS |

### Detailed Sample Breakdown

| ID | Category | Expected Route | Actual Route | Faithfulness | Relevance | Guardrail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `eval_001` | rag | `rag` | `rag` | `1.00` | `0.96` | Passed |
| `eval_002` | rag | `rag` | `rag` | `1.00` | `0.96` | Passed |
| `eval_003` | rag | `rag` | `rag` | `1.00` | `0.95` | Passed |
| `eval_004` | rag | `rag` | `rag` | `1.00` | `0.95` | Passed |
| `eval_005` | rag | `rag` | `rag` | `1.00` | `0.81` | Passed |
| `eval_006` | rag | `rag` | `rag` | `1.00` | `0.48` | Passed |
| `eval_007` | rag | `rag` | `tool` | `1.00` | `0.51` | Passed |
| `eval_008` | rag | `rag` | `rag` | `1.00` | `0.51` | Passed |
| `eval_009` | rag | `rag` | `rag` | `1.00` | `0.47` | Passed |
| `eval_010` | rag | `rag` | `rag` | `1.00` | `0.83` | Passed |