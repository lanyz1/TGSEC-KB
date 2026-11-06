# Media / CDN Failure Triage

Use when links are correct but the page shows no images. The failure is usually DNS, origin, edge, or mixed content; identify the layer before changing any setting.

## 1. Extract the real image hosts

```bash
curl -sS 'https://<ENTRY_HOST>/entry/<CID>?v=1' -o /tmp/page.html
grep -oE 'https?://[^"'"'"' <>]+' /tmp/page.html \
  | sed -E 's#^https?://([^/]+).*#\1#' | sort | uniq -c | sort -rn | head
```

If every image points to one host, test that host first. A low-count placeholder host in the page config is not necessarily the image source.

## 2. Distinguish DNS from origin and edge

```bash
# DNS layer: NXDOMAIN here means the browser cannot even reach the edge.
getent hosts <IMG_HOST>
dig +short <IMG_HOST> A
dig +short <IMG_HOST> CNAME

# Origin layer: if the object store serves the object, the asset exists.
curl -sS -m 15 -o /tmp/img -w '%{http_code} %{content_type} %{size_download}\n' \
  'http://<ORIGIN_HOST>/<BUCKET>/<PATH>'

# Edge layer: force the recorded edge IP while keeping the Host/SNI.
for ip in <EDGE_IP_1> <EDGE_IP_2>; do
  curl -sS -m 15 --resolve <IMG_HOST>:443:$ip \
    -o /tmp/img -w "$ip %{http_code} %{content_type} %{size_download}\n" \
    "https://<IMG_HOST>/<PATH>"
done

# Certificate must cover the host used by the page.
echo | openssl s_client -connect <EDGE_IP>:443 -servername <IMG_HOST> 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
```

## 3. Read the result

| DNS | Origin | Edge with Host | Diagnosis |
|---|---|---|---|
| NXDOMAIN | 200 | 200 | DNS record dead; fix DNS, not the app setting |
| NXDOMAIN | 200 | 404 | Edge site/origin mapping wrong; not an app fix |
| resolves | 404 | 404 | Asset path/bucket wrong |
| resolves | 200 | cert mismatch | Wrong CDN host; use the host the cert covers |

If the edge returns the image with the original Host, an A record to the edge IPs is sufficient:

```
<IMG_HOST>  A  <EDGE_IP_1>
<IMG_HOST>  A  <EDGE_IP_2>
```

Do not point the app's `IMG_DOMAIN` at a CNAME host whose certificate does not include that host; the browser will reject it even if the edge serves the object.

## 4. Mixed content

An HTTPS page loading `http://<origin>` is blocked by the browser. If the only working asset URL is HTTP object storage, the correct fix is an HTTPS CDN/proxy, not changing `IMG_DOMAIN` to the HTTP origin. Do not claim the page is fixed until an HTTPS image URL returns 200.

## 5. What not to do

- Do not change `IMG_DOMAIN`/`IMAGE_DOMAIN_NAME` before testing DNS, origin, and edge; a placeholder setting is often not the cause.
- Do not trust browser cache; the root page may show cached images while a new entry route fails.
- Do not report success from a single `curl` that used `--resolve`; the user's browser still needs a resolvable DNS record or a working public host.
