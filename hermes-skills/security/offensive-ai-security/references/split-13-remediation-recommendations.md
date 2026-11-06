## Remediation Recommendations

Strategies to prevent and fix AI/LLM vulnerabilities:

| Vulnerability          | Key Mitigations                                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------------------------------- |
| Prompt Injection       | Sanitize inputs, use parameterization, implement instruction defense, adopt least privilege, define I/O schemas |
| Insecure Output        | Validate and sanitize outputs, apply principle of least privilege, implement CSP for web content                |
| Data Poisoning         | Vet data sources, implement sanitization and anomaly detection, maintain provenance, conduct regular audits     |
| Denial of Service      | Validate inputs (length, complexity), implement resource limits and timeouts, use async processing              |
| Supply Chain           | Secure MLOps pipeline, scan dependencies (AI-BOM), use trusted registries, implement access controls            |
| Information Disclosure | Practice data minimization, implement redaction/anonymization, filter I/O for sensitive patterns                |
| Insecure Plugins       | Validate inputs, implement least privilege, require auth, use parameterized calls, conduct security audits      |
| Excessive Agency       | Limit LLM capabilities, implement human-in-the-loop, scope permissions tightly, monitor LLM actions             |
| RAG Embedding Leakage  | Encrypt vector indices at rest, enforce row‑level ACLs, implement access‑pattern privacy (e.g., OPAL)           |
| Overreliance           | Educate users on limitations, implement verification mechanisms, clearly mark AI-generated content              |
| Model Theft            | Secure APIs and infrastructure, implement watermarking, enforce legal agreements, limit model exposure          |

