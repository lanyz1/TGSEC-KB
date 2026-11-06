## Bridge to neighboring skills

- `apk-redteam-pipeline` — APKs reveal internal package names too (find them in decompiled `build.gradle`)
- `cloud-iam-deep` — CI/CD secrets often = cloud credentials; this skill finds them, that skill validates them
- `hunt-cloud-misconfig` — CI/CD pipeline misconfig (Jenkins / GitLab Runner) overlap
- `m365-entra-attack` — Azure DevOps pipelines are part of Entra surface
- `redteam-report-template` — supply-chain findings need extra clarity on blast radius (one repo vs whole ecosystem)
- `mid-engagement-ir-detection` — registering a name on public npm triggers nothing inside the client, but ANY publish action is loud and audit-trailed

---

