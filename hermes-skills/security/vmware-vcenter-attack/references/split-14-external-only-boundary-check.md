## External-only boundary check

If recon reveals vCenter only via VPN (not direct internet) → STOP. That is internal infrastructure and outside the external-only AI scope per `feedback_skill_boundaries`. The user handles internal vCenter work directly.

Internet-exposed vCenter is unfortunately common on the perimeter — and frequently outdated by years. The 2021-21972 / 21985 / 22954 trifecta still pays in 2026 because patching cycles for hypervisor management are slow and vendor-managed.

---

