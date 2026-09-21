# Security Policy — VAYUBODHAK

## 1. Supported Versions

| Version | Supported | Security Maintenance |
| :--- | :--- | :--- |
| 1.0.x (Current) | **Yes** | Active security patches and vulnerability remediation |

---

## 2. Reporting a Vulnerability

The VAYUBODHAK team takes security, source authority integrity, and data privacy seriously. If you discover a security vulnerability or authority bypass issue, please follow our responsible disclosure process:

1. **Do NOT open a public GitHub issue.**
2. Send a detailed report to the security maintainers at: `security@vayubodhak.internal` (or repository owner contact).
3. Include:
   * Type of vulnerability (e.g. Authentication bypass, SQL injection, RBAC privilege escalation, Source spoofing).
   * Steps to reproduce the issue.
   * Proof-of-concept payload or execution trace.
   * Potential impact assessment.
4. You will receive an acknowledgment within 48 hours, followed by regular status updates as a patch is developed and verified.

---

## 3. Core Security & Authority Principles

1. **Prohibition of Fabricated Statutory Authority**:
   * Any mechanism or code that attempts to falsely impersonate government statutory bodies (IMD, CWC, NDMA) or falsely certify non-statutory data as an official emergency warning is classified as a Critical Severity Security Defect.
2. **Credential & Secret Protection**:
   * No API keys, JWT secrets, passwords, or production database credentials may be committed to version control.
   * The repository strictly uses environment variables loaded through `.env` with a non-sensitive `.env.example` template.
3. **Role-Based Access Control (RBAC)**:
   * Internal showcase scenarios, administrative endpoints, and manual override capabilities are strictly gated by cryptographic token authorization.
