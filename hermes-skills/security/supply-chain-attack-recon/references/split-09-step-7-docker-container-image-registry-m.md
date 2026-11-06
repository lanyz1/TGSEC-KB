## Step 7 — Docker / container image registry mining

```bash
# Docker Hub
curl -s "https://hub.docker.com/v2/repositories/$ORG/?page_size=100" | jq -r '.results[].name'

# GHCR (GitHub Container Registry) — public images visible in repo packages tab
gh api "users/$ORG/packages?package_type=container" 2>/dev/null
gh api "orgs/$ORG/packages?package_type=container" 2>/dev/null

# For each image, list tags
for img in image1 image2; do
  curl -s "https://hub.docker.com/v2/repositories/$ORG/$img/tags?page_size=20" | jq -r '.results[].name'
done

# Pull and inspect layers
docker pull "$ORG/$img:latest"
docker history --no-trunc "$ORG/$img:latest"

# Mine layers for secrets
docker save "$ORG/$img:latest" -o /tmp/image.tar
mkdir -p /tmp/img && tar -xf /tmp/image.tar -C /tmp/img
find /tmp/img -name "*.tar*" -exec tar -xf {} -C /tmp/img/extracted \;
# Then run gitleaks / trufflehog over extracted filesystem
trufflehog filesystem /tmp/img/extracted --no-update
```

---

