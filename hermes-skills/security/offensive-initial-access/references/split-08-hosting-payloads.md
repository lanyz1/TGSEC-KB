## Hosting Payloads

- Server Hosting our Payload must
  - Look benign, best if commonly used for file hosting
  - Have SSL/TLS certificate signed by trusted authority
  - Hard to be blocked by target (cloud based)
- Example
  - Cloud-based file storage: Office365 OneDrive, SharePoint, AWS S3, MS Azure Storage, Google Drive, FireBase Storage
  - CDN: Azure Edge CDN, StackPath, Fastly, Akamai, Google Cloud AppSpot, HerokuApp
  - Serverless Endpoints: AWS Lambda, CloudFlare Workers, DigitalOcean Apps
- use [LOTS Project](https://lots-project.com/) for help
- use [LOLBINS](https://lolbas-project.github.io/)
  - prefer DLL over EXE
  - indirect execution to circumvent EDR/AV
  - DLL Side-Loading / DLL Hijacking / COM Hijacking / XLL
- check [Microsoft Block Rules](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/windows-defender-application-control/design/applications-that-can-bypass-wdac) to better circumvent defender

