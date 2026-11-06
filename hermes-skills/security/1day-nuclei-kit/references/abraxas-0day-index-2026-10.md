# abraxas 0day 系列索引（2026-10-11 ~ 10-18）

> 来源: https://github.com/abraxas （254 repos，其中 152 个 created ≥ 2026-10-10，GitHub API 核验）

> 性质: **作者自研 0day，未分配 CVE**，仓库描述即攻击面声明；版本是作者测试环境版本，不等于官方受影响范围。

> 纪律: 本索引只记「哪个产品的哪个字段/接口是什么性质的问题」。利用细节、前置条件、复现步骤看各仓库 README 与 abraxaslabs.tech 对应 write-up。**不要**把这里当 NVD 已确认漏洞引用。

> 用法: 目标指纹命中产品+版本 → 按产品段定位候选仓库 → 只读验证（版本回显/参数行为差分），写权限/执行链放到授权 lab。


总计 152 个仓库，26 个产品族。


## pfSense（53）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [pfsense-ipsec-login-banner](https://github.com/abraxas/pfsense-ipsec-login-banner) | 2026-10-13 | pfSense CE 2.9.0-DEVELOPMENT | High | IPsec login_banner start-scripts |
| [pfsense-openvpn-wizard-crlf](https://github.com/abraxas/pfsense-openvpn-wizard-crlf) | 2026-10-13 | pfSense CE 2.9.0-DEVELOPMENT | High | OpenVPN wizard CRLF |
| [pfsense-qinq-parent-if](https://github.com/abraxas/pfsense-qinq-parent-if) | 2026-10-13 | pfSense CE 2.9.0-DEVELOPMENT | High | QinQ parent-if ifconfig |
| [pfsense-limiter-number](https://github.com/abraxas/pfsense-limiter-number) | 2026-10-13 | pfSense CE 2.9.0-DEVELOPMENT | High | limiter number dnctl |
| [pfsense-carp-vhid](https://github.com/abraxas/pfsense-carp-vhid) | 2026-10-13 | pfSense CE 2.9.0-DEVELOPMENT | High | CARP VHID leftover |
| [pfsense-api-enroll-json-ssh](https://github.com/abraxas/pfsense-api-enroll-json-ssh) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | example-add-devices.py JSON into SSH |
| [pfsense-api-export-key-get](https://github.com/abraxas/pfsense-api-export-key-get) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | GET export-key private keys |
| [pfsense-api-fleet-jwt](https://github.com/abraxas/pfsense-api-fleet-jwt) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | one controller JWT is a fleet token |
| [pfsense-api-snort-file-join](https://github.com/abraxas/pfsense-api-snort-file-join) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | Snort rules {file} decode-then-join |
| [pfsense-api-acme-key-dump](https://github.com/abraxas/pfsense-api-acme-key-dump) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | GET /services/acme dumps keys |
| [pfsense-api-enroll-autoadd](https://github.com/abraxas/pfsense-api-enroll-autoadd) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | Paramiko AutoAddPolicy enroll |
| [pfsense-api-unix-sock-noauth](https://github.com/abraxas/pfsense-api-unix-sock-noauth) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | unix sock enroll no JWT |
| [pfsense-api-example-ssl-verify](https://github.com/abraxas/pfsense-api-example-ssl-verify) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | Medium | official samples verify_ssl=False |
| [pfsense-api-acb-userkey](https://github.com/abraxas/pfsense-api-acb-userkey) | 2026-10-15 | pfSense Plus MIM API toolkit b4acd7ca | High | ACB userkey capability URL |
| [pfsense-wireless-clone](https://github.com/abraxas/pfsense-wireless-clone) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | wireless clone ifconfig |
| [pfsense-timezone-phpini](https://github.com/abraxas/pfsense-timezone-phpini) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | timezone php.ini prepend |
| [pfsense-assign-if-add](https://github.com/abraxas/pfsense-assign-if-add) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | assign Add if_add |
| [pfsense-gw-ipv6-zone](https://github.com/abraxas/pfsense-gw-ipv6-zone) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | IPv6 zone into dpinger |
| [pfsense-l2tp-radius-mpd](https://github.com/abraxas/pfsense-l2tp-radius-mpd) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | L2TP RADIUS mpd.conf |
| [pfsense-cp-ha-pfctl](https://github.com/abraxas/pfsense-cp-ha-pfctl) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | CP HA host into pfctl |
| [pfsense-pppoe-cron](https://github.com/abraxas/pfsense-pppoe-cron) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | PPPoE ptpid crontab |
| [pfsense-sshguard-crlf](https://github.com/abraxas/pfsense-sshguard-crlf) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | sshguard THRESHOLD CRLF |
| [pfsense-pppoe-secret-bang](https://github.com/abraxas/pfsense-pppoe-secret-bang) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | PPPoE mpd.secret bang |
| [pfsense-ldap-name-collision](https://github.com/abraxas/pfsense-ldap-name-collision) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | LDAP admin name |
| [pfsense-acb-restore-priv](https://github.com/abraxas/pfsense-acb-restore-priv) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | ACB restore |
| [pfsense-wizard-uid0](https://github.com/abraxas/pfsense-wizard-uid0) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | wizard uid 0 |
| [pfsense-unbound-acl-crlf](https://github.com/abraxas/pfsense-unbound-acl-crlf) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | Unbound ACL CRLF include |
| [pfsense-dyndns-file](https://github.com/abraxas/pfsense-dyndns-file) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | DynDNS file:// |
| [pfsense-ovpn-connect-eval](https://github.com/abraxas/pfsense-ovpn-connect-eval) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | OpenVPN connect eval |
| [pfsense-unbound-sock-timeout](https://github.com/abraxas/pfsense-unbound-sock-timeout) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | Unbound sock-queue-timeout CRLF |
| [pfsense-ovpn-learn-cn](https://github.com/abraxas/pfsense-ovpn-learn-cn) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | OpenVPN learn-address CN |
| [pfsense-cp-filemanager-write](https://github.com/abraxas/pfsense-cp-filemanager-write) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | CP file manager |
| [pfsense-uploadconfig](https://github.com/abraxas/pfsense-uploadconfig) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | hidden uploadconfig |
| [pfsense-rss-file-redirect](https://github.com/abraxas/pfsense-rss-file-redirect) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | RSS file:// redirect |
| [pfsense-rules-if-xss](https://github.com/abraxas/pfsense-rules-if-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | firewall_rules GET if |
| [pfsense-logs-filter-xss](https://github.com/abraxas/pfsense-logs-filter-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | logs filter JSON as HTML |
| [pfsense-cp-filename-xss](https://github.com/abraxas/pfsense-cp-filename-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | CP filename stored XSS |
| [pfsense-cp-maxprocperip](https://github.com/abraxas/pfsense-cp-maxprocperip) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | CP maxprocperip nginx |
| [pfsense-rss-body-xss](https://github.com/abraxas/pfsense-rss-body-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | RSS body leftover of 26_04 |
| [pfsense-separator-color-xss](https://github.com/abraxas/pfsense-separator-color-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | separator color into class |
| [pfsense-auth-username-xss](https://github.com/abraxas/pfsense-auth-username-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | LDAP username in head.inc |
| [pfsense-config-readonly-restore](https://github.com/abraxas/pfsense-config-readonly-restore) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | High | readonly config_install |
| [pfsense-crash-reporter-xss](https://github.com/abraxas/pfsense-crash-reporter-xss) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | crash_reporter textarea |
| [pfsense-dyndns-cache-path](https://github.com/abraxas/pfsense-dyndns-cache-path) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | DynDNS cache path |
| [pfsense-limiter-aqm](https://github.com/abraxas/pfsense-limiter-aqm) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | limiter AQM newline |
| [pfsense-bsnmpd-conf](https://github.com/abraxas/pfsense-bsnmpd-conf) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | bsnmpd syslocation |
| [pfsense-vlan-parent-ioctl](https://github.com/abraxas/pfsense-vlan-parent-ioctl) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Low | VLAN parent not in portlist |
| [pfsense-igmp-type](https://github.com/abraxas/pfsense-igmp-type) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | IGMP type newline |
| [pfsense-wol-get-all](https://github.com/abraxas/pfsense-wol-get-all) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Low | WOL GET wakeall |
| [pfsense-https-host-redirect](https://github.com/abraxas/pfsense-https-host-redirect) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | HTTP 301 $http_host |
| [pfsense-voucher-expire-sqli](https://github.com/abraxas/pfsense-voucher-expire-sqli) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | voucher_expire WHERE |
| [pfsense-ntp-gps-fudge](https://github.com/abraxas/pfsense-ntp-gps-fudge) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | NTP GPS/PPS fudge |
| [pfsense-dhcpd-conf](https://github.com/abraxas/pfsense-dhcpd-conf) | 2026-10-15 | pfSense CE 2.9.0-DEVELOPMENT | Medium | ISC dhcpd filename |

## OPNsense（7）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [opnsense-tunables-loader](https://github.com/abraxas/opnsense-tunables-loader) | 2026-10-13 | OPNsense 26.7.6 | High | tunables loader |
| [opnsense-wlan-wpa-line](https://github.com/abraxas/opnsense-wlan-wpa-line) | 2026-10-13 | OPNsense 26.7.6 | High | WLAN WPA identity |
| [opnsense-captive-lastseen-roam](https://github.com/abraxas/opnsense-captive-lastseen-roam) | 2026-10-13 | OPNsense 26.7.6 | High | captive lastseen roam |
| [opnsense-ntp-gps-fudge](https://github.com/abraxas/opnsense-ntp-gps-fudge) | 2026-10-13 | OPNsense 26.7.6 | High | NTP GPS fudge |
| [opnsense-lockout-factory-ip](https://github.com/abraxas/opnsense-lockout-factory-ip) | 2026-10-13 | OPNsense 26.7.6 | High | factory lockout IP |
| [opnsense-uidfield-system-uid0](https://github.com/abraxas/opnsense-uidfield-system-uid0) | 2026-10-13 | OPNsense 26.7.6 | High | UidField uid 0 |
| [opnsense-firmware-mirror-sed](https://github.com/abraxas/opnsense-firmware-mirror-sed) | 2026-10-13 | OPNsense 26.7.6 | High | custom firmware mirror sed-skips pkg fingerprints |

## Apache Spark（9）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [spark-rpc-stream-unauth](https://github.com/abraxas/spark-rpc-stream-unauth) | 2026-10-13 | Apache Spark 4.2.0 | High | unauth RPC StreamRequest File join |
| [spark-history-store-path](https://github.com/abraxas/spark-history-store-path) | 2026-10-13 | Apache Spark 4.2.0 | High | History appStorePath unsanitized App ID |
| [spark-rest-auth-bypass](https://github.com/abraxas/spark-rest-auth-bypass) | 2026-10-13 | Apache Spark 4.2.0 | High | standalone REST ignores spark.authenticate |
| [spark-connect-archive-fragment](https://github.com/abraxas/spark-connect-archive-fragment) | 2026-10-13 | Apache Spark 4.2.0 | High | Connect archives hash-fragment dest |
| [spark-connect-copy-local](https://github.com/abraxas/spark-connect-copy-local) | 2026-10-13 | Apache Spark 4.2.0 | High | Connect session SET copyFromLocalToFs.allowDestLocal |
| [spark-history-zip-symlink](https://github.com/abraxas/spark-history-zip-symlink) | 2026-10-13 | Apache Spark 4.2.0 | High | History zip follows planted symlink |
| [spark-python-ds-static](https://github.com/abraxas/spark-python-ds-static) | 2026-10-13 | Apache Spark 4.2.0 | High | process-global Python Data Source map |
| [spark-proxyuser-classpath](https://github.com/abraxas/spark-proxyuser-classpath) | 2026-10-13 | Apache Spark 4.2.0 | High | proxy-user defaultExtraClassPath |
| [spark-jdbc-serde-url](https://github.com/abraxas/spark-jdbc-serde-url) | 2026-10-13 | Apache Spark 4.2.0 | High | ALTER TABLE SET SERDEPROPERTIES |

## Apache Tomcat（1）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [tomcat-rewrite-ns-loop](https://github.com/abraxas/tomcat-rewrite-ns-loop) | 2026-10-12 | Apache Tomcat 11.0.27 | High | RewriteValve [NS] worker pin |

## Apache OpenMeetings（12）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [openmeetings-backup-config-path](https://github.com/abraxas/openmeetings-backup-config-path) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | ADMIN_BACKUP import skips Path.of on Type.PATH |
| [openmeetings-kms-unauth](https://github.com/abraxas/openmeetings-kms-unauth) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | docs docker publishes Kurento JSON-RPC on 8888 |
| [openmeetings-stale-install-admin](https://github.com/abraxas/openmeetings-stale-install-admin) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | stale /install wizard inserts second ADMIN |
| [openmeetings-calendar-save-idor](https://github.com/abraxas/openmeetings-calendar-save-idor) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | LOGIN calendar save overwrites appointment and closes public room |
| [openmeetings-soap-otp-skip](https://github.com/abraxas/openmeetings-soap-otp-skip) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | SOAP/REST password login skips TOTP |
| [openmeetings-nettest-ping-dos](https://github.com/abraxas/openmeetings-nettest-ping-dos) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | unauth NetTest ping POST reads body to EOF |
| [openmeetings-remember-me-password](https://github.com/abraxas/openmeetings-remember-me-password) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | remember-me cookie replay authenticates without password |
| [openmeetings-chat-user-idor](https://github.com/abraxas/openmeetings-chat-user-idor) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | dashboard chatTab-u{id} exports another users private chat |
| [openmeetings-soap-user-rights](https://github.com/abraxas/openmeetings-soap-user-rights) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | SOAP POST /user copies UserDTO.rights including ADMIN |
| [openmeetings-wb-fileid-idor](https://github.com/abraxas/openmeetings-wb-fileid-idor) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | WHITEBOARD fileId plant then room file resource serves bytes |
| [openmeetings-invite-recording-acl](https://github.com/abraxas/openmeetings-invite-recording-acl) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | Type.USER invitation recording MP4 ACL |
| [openmeetings-cluster-openjpa](https://github.com/abraxas/openmeetings-cluster-openjpa) | 2026-10-16 | Apache OpenMeetings 9.1.0 | High | clustering OpenJPA RemoteCommitProvider TCP 5636 |

## Jellyfin（4）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [jellyfin-svg-gzip](https://github.com/abraxas/jellyfin-svg-gzip) | 2026-10-17 | Jellyfin Server 12.2 | High | gzip data:image/png leftover of GHSA-cf3c still fetches http and file |
| [jellyfin-ffmpeg-colonslash](https://github.com/abraxas/jellyfin-ffmpeg-colonslash) | 2026-10-17 | Jellyfin Server 12.2 | High | EncodingUtils -i leftover of GHSA-wwwm |
| [jellyfin-suggestions-idor](https://github.com/abraxas/jellyfin-suggestions-idor) | 2026-10-17 | Jellyfin Server 12.2 | High | GET /Items/Suggestions omit-userId dumps hidden library Path and IDs |
| [jellyfin-playlist-itemids](https://github.com/abraxas/jellyfin-playlist-itemids) | 2026-10-17 | Jellyfin Server 12.2 | High | public playlist ItemIds leftover of GHSA-9x85 then unauth stream |

## Stirling-PDF（2）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [stirling-storage-folder-idor](https://github.com/abraxas/stirling-storage-folder-idor) | 2026-10-17 | Stirling-PDF v3.2.0 | High | processing-folder storage root lists and overwrites peer PDFs |
| [stirling-h2-import-leftover](https://github.com/abraxas/stirling-h2-import-leftover) | 2026-10-17 | Stirling-PDF v3.2.0 | Critical | CREATE OR REPLACE ALIAS import-database |

## Plausible Analytics（2）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [plausible-editor-invite](https://github.com/abraxas/plausible-editor-invite) | 2026-10-18 | Plausible Analytics master d44e104 | High | editor people HTML leaks transfer nanoid |
| [plausible-traffic-notify](https://github.com/abraxas/plausible-traffic-notify) | 2026-10-18 | Plausible Analytics master d44e104 | High | PUT traffic-change-notification site_id mass assignment |

## Drupal（4）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [drupal-htmx-attr](https://github.com/abraxas/drupal-htmx-attr) | 2026-10-12 | Drupal 11.4.8 | High | AttributeXss still allows HTMX attrs |
| [drupal-ckeditor-fileisimage](https://github.com/abraxas/drupal-ckeditor-fileisimage) | 2026-10-12 | Drupal 11.4.8 | High | CKEditor 5 image upload still skips FileIsImage |
| [drupal-move-block-markup](https://github.com/abraxas/drupal-move-block-markup) | 2026-10-12 | Drupal 11.4.8 | High | Move Block sibling labels skip @label escaping |
| [drupal-oembed-ssrf](https://github.com/abraxas/drupal-oembed-ssrf) | 2026-10-12 | Drupal 11.4.8 | High | oEmbed discovery GETs an unscoped second-hop URL |

## Joomla（4）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [joomla-levels-api](https://github.com/abraxas/joomla-levels-api) | 2026-10-12 | Joomla 6.1.3 | High | GET /api/v1/users/levels leaks view levels |
| [joomla-menu-items-api](https://github.com/abraxas/joomla-menu-items-api) | 2026-10-12 | Joomla 6.1.3 | High | menu items API leftover |
| [joomla-media-override](https://github.com/abraxas/joomla-media-override) | 2026-10-12 | Joomla 6.1.3 | High | media manager overwrite leftover |
| [joomla-articles-catid](https://github.com/abraxas/joomla-articles-catid) | 2026-10-12 | Joomla 6.1.3 | High | POST /api/v1/content/articles ignores per-category ACL |

## Moodle（4）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [moodle-blackboard-img](https://github.com/abraxas/moodle-blackboard-img) | 2026-10-12 | Moodle 5.2.3 | High | Blackboard img src copies files outside the import tree |
| [moodle-grades-feedback-idor](https://github.com/abraxas/moodle-grades-feedback-idor) | 2026-10-12 | Moodle 5.2.3 | High | core_grades_get_feedback skips separate-groups checks |
| [moodle-enrol-database-sqli](https://github.com/abraxas/moodle-enrol-database-sqli) | 2026-10-12 | Moodle 5.2.3 | High | enrol_database concatenates course idnumber into SQL |
| [moodle-grades-gradeitems](https://github.com/abraxas/moodle-grades-gradeitems) | 2026-10-12 | Moodle 5.2.3 | High | core_grades_get_gradeitems lists hidden grade items |

## CakePHP（7）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [cakephp-smtp-crlf](https://github.com/abraxas/cakephp-smtp-crlf) | 2026-10-12 | CakePHP 5.4.2 | High | SmtpTransport lone LF leftover of GHSA-2qh5 |
| [cakephp-cookie-suffix](https://github.com/abraxas/cakephp-cookie-suffix) | 2026-10-12 | CakePHP 5.4.2 | High | Http Client cookie jar matches domains as a regex suffix |
| [cakephp-trusted-proxies](https://github.com/abraxas/cakephp-trusted-proxies) | 2026-10-12 | CakePHP 5.4.2 | High | trustedProxies honors X-Forwarded-* from any REMOTE_ADDR |
| [cakephp-window-sqli](https://github.com/abraxas/cakephp-window-sqli) | 2026-10-12 | CakePHP 5.4.2 | High | WindowExpression range/frame offsets spliced into SQL |
| [cakephp-attachment-crlf](https://github.com/abraxas/cakephp-attachment-crlf) | 2026-10-12 | CakePHP 5.4.2 | High | attachment Content-Type and Content-ID leftover |
| [cakephp-collate-sqli](https://github.com/abraxas/cakephp-collate-sqli) | 2026-10-12 | CakePHP 5.4.2 | High | COLLATE collation is a raw SQL fragment |
| [cakephp-cache-unserialize](https://github.com/abraxas/cakephp-cache-unserialize) | 2026-10-12 | CakePHP 5.4.2 | High | cache engines unserialize objects with no class allowlist |

## Element（3）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [element-fragment-guest](https://github.com/abraxas/element-fragment-guest) | 2026-10-12 | Element Web v1.12.29 | High | fragment guest creds wipe a real session before whoami |
| [element-ics-javascript](https://github.com/abraxas/element-ics-javascript) | 2026-10-12 | Element Web v1.12.29 | High | Univention ICS navigation.json link becomes a javascript: menu href |
| [element-vector-drive-letter](https://github.com/abraxas/element-vector-drive-letter) | 2026-10-12 | Element Desktop v1.12.29 | High | vector: protocol reads Windows files outside the asar jail |

## vsftpd（3）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [vsftpd-ssl-data-any-ticket](https://github.com/abraxas/vsftpd-ssl-data-any-ticket) | 2026-10-12 | vsftpd 3.0.5 | High | FTPS data accepts any resumed ticket |
| [vsftpd-cmds-denied-alias](https://github.com/abraxas/vsftpd-cmds-denied-alias) | 2026-10-12 | vsftpd 3.0.5 | High | cmds_denied misses RFC aliases (XRMD) |
| [vsftpd-deny-file-brace-child](https://github.com/abraxas/vsftpd-deny-file-brace-child) | 2026-10-12 | vsftpd 3.0.5 | High | brace deny_file misses .private/secret |

## ProFTPD（3）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [proftpd-rewrite-utf8trans](https://github.com/abraxas/proftpd-rewrite-utf8trans) | 2026-10-12 | ProFTPD 1.3.9d | High | RewriteMap int:utf8trans BSS overflow |
| [proftpd-sftp-copy-file-write](https://github.com/abraxas/proftpd-sftp-copy-file-write) | 2026-10-12 | ProFTPD 1.3.9d | High | SFTP copy-file skips dest WRITE |
| [proftpd-site-copy-dest-follow](https://github.com/abraxas/proftpd-site-copy-dest-follow) | 2026-10-12 | ProFTPD 1.3.9d | High | SITE COPY dest follows symlink |

## lighttpd（1）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [lighttpd-win32-dotdot-space](https://github.com/abraxas/lighttpd-win32-dotdot-space) | 2026-10-12 | lighttpd 1.4.85 | High | native Win32 GET /..%20/ reads outside document-root |

## OpenLiteSpeed（1）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [openlitespeed-h3-mtls-verifycontext](https://github.com/abraxas/openlitespeed-h3-mtls-verifycontext) | 2026-10-12 | OpenLiteSpeed 1.9.3 | High | HTTP/3 skips Host-vs-SNI bind |

## phpMyAdmin（10）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [phpmyadmin-pmadb-central-sqli](https://github.com/abraxas/phpmyadmin-pmadb-central-sqli) | 2026-10-12 | phpMyAdmin 5.2.3 | High | central columns pmadb query leftover |
| [phpmyadmin-webauthn](https://github.com/abraxas/phpmyadmin-webauthn) | 2026-10-12 | phpMyAdmin 5.2.3 | High | WebAuthn ceremony can be skipped |
| [phpmyadmin-designer-json-sqli](https://github.com/abraxas/phpmyadmin-designer-json-sqli) | 2026-10-12 | phpMyAdmin 5.2.3 | High | Designer JSON unsanitized identifiers |
| [phpmyadmin-csrf-sql](https://github.com/abraxas/phpmyadmin-csrf-sql) | 2026-10-12 | phpMyAdmin 5.2.3 | High | token strip on /sql |
| [phpmyadmin-setup-validate](https://github.com/abraxas/phpmyadmin-setup-validate) | 2026-10-12 | phpMyAdmin 5.2.3 | High | setup/validate still reachable |
| [phpmyadmin-auth-plugin-unquoted](https://github.com/abraxas/phpmyadmin-auth-plugin-unquoted) | 2026-10-12 | phpMyAdmin 5.2.3 | High | auth plugin identifier unquoted |
| [phpmyadmin-vqb-xss](https://github.com/abraxas/phpmyadmin-vqb-xss) | 2026-10-12 | phpMyAdmin 5.2.3 | High | Designer Visual Query Builder |
| [phpmyadmin-issuperuser](https://github.com/abraxas/phpmyadmin-issuperuser) | 2026-10-12 | phpMyAdmin 5.2.3 | High | isSuperUser check skipped |
| [phpmyadmin-config-set-2fa](https://github.com/abraxas/phpmyadmin-config-set-2fa) | 2026-10-12 | phpMyAdmin 5.2.3 | High | config/set clears two-factor |
| [phpmyadmin-importldi](https://github.com/abraxas/phpmyadmin-importldi) | 2026-10-12 | phpMyAdmin 5.2.3 | High | ImportLdi TERMINATED BY leftover |

## PostgreSQL（1）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [postgres-basebackup-symlink](https://github.com/abraxas/postgres-basebackup-symlink) | 2026-10-12 | PostgreSQL 18.6 | High | pg_basebackup follows absolute tar symlink leftover of CVE-2026-6475 |

## Forgejo（4）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [forgejo-keys-idor](https://github.com/abraxas/forgejo-keys-idor) | 2026-10-12 | Forgejo 16.0.5 | High | GET /api/v1/user/keys/{id} returns other users SSH and deploy keys |
| [forgejo-hostmatcher-0001-ssrf](https://github.com/abraxas/forgejo-hostmatcher-0001-ssrf) | 2026-10-12 | Forgejo 16.0.5 | High | hostmatcher allows 0.0.0.1 as a public IP |
| [forgejo-restore-file-open](https://github.com/abraxas/forgejo-restore-file-open) | 2026-10-12 | Forgejo 16.0.5 | High | restore-repo follows dump-side file:// into attachments |
| [forgejo-openid-discovery-ssrf](https://github.com/abraxas/forgejo-openid-discovery-ssrf) | 2026-10-12 | Forgejo 16.0.5 | High | OpenID discovery fetches attacker-controlled URLs |

## Grafana（2）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [grafana-gitsync-dns-rebind](https://github.com/abraxas/grafana-gitsync-dns-rebind) | 2026-10-12 | Grafana OSS 13.2.3 | High | Git Sync URLValidator is admission-only DNS |
| [grafana-signup-invite-join](https://github.com/abraxas/grafana-signup-invite-join) | 2026-10-12 | Grafana OSS 13.2.3 | High | SignUpStep2 joins pending org invites without the code |

## Prometheus（2）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [prometheus-bearer-redirect](https://github.com/abraxas/prometheus-bearer-redirect) | 2026-10-12 | Prometheus v3.15.0 | High | remote_write google_iam/azuread forwards Bearer on cross-host 3xx |
| [prometheus-unix-socket-dial](https://github.com/abraxas/prometheus-unix-socket-dial) | 2026-10-12 | Prometheus v3.15.0 | High | http_sd __unix_socket__ unsanitized Dial leftover of UDS scrape |

## Signal Server（1）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [signal-server-dropwizard-admin](https://github.com/abraxas/signal-server-dropwizard-admin) | 2026-10-11 | Signal-Server v20261007.0.0 | High | unauth Dropwizard admin :8081 |

## VFS for Git（6）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [vfs-mount-dehydrate](https://github.com/abraxas/vfs-mount-dehydrate) | 2026-10-12 | VFS for Git ab95cf51 | High | Users mount pipe dehydrate/unmount |
| [vfs-install-cwd](https://github.com/abraxas/vfs-install-cwd) | 2026-10-12 | VFS for Git ab95cf51 | High | installer CWD unqualified gvfs.exe |
| [vfs-quote-breakout](https://github.com/abraxas/vfs-quote-breakout) | 2026-10-12 | VFS for Git ab95cf51 | High | core.virtualfilesystem single-quote wrap |
| [vfs-hook-impersonate](https://github.com/abraxas/vfs-hook-impersonate) | 2026-10-12 | VFS for Git ab95cf51 | High | hook CreateFileW SecurityImpersonation |
| [vfs-service-sid](https://github.com/abraxas/vfs-service-sid) | 2026-10-12 | VFS for Git ab95cf51 | Medium | service pipe trusts JSON OwnerSID |
| [vfs-clone-acl](https://github.com/abraxas/vfs-clone-acl) | 2026-10-12 | VFS for Git ab95cf51 | High | clone Authenticated Users GENERIC_WRITE |

## QEMU（3）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [qemu-nvme-sgl-bar](https://github.com/abraxas/qemu-nvme-sgl-bar) | 2026-10-17 | QEMU 11.1.2 | High | NVMe SGL span into BAR0 incomplete CVE-2021-3929 |
| [qemu-xhci-complete-uaf](https://github.com/abraxas/qemu-xhci-complete-uaf) | 2026-10-17 | QEMU 11.1.2 | High | xhci_complete leftover of CVE-2026-17588 doorbell DMA |
| [qemu-colo-l4-oob](https://github.com/abraxas/qemu-colo-l4-oob) | 2026-10-17 | QEMU 11.1.2 | High | COLO filter-rewriter short IPv4 L4 heap overflow |

## LiteBox（3）

| 仓库 | 建仓 | 版本/声明 | 级别 | 类型与原语 |
|---|---|---|---|---|
| [litebox-seccomp-open-rdonly](https://github.com/abraxas/litebox-seccomp-open-rdonly) | 2026-10-12 | High local file read: LiteBox v0.1.0 linux-userland seccomp SYS_open O |  |  |
| [litebox-snp-fixed-crng](https://github.com/abraxas/litebox-snp-fixed-crng) | 2026-10-12 | High local crypto: LiteBox v0.1.0 SNP CrngProvider is public-seed Fast |  |  |
| [litebox-snp-novalidation-userptr](https://github.com/abraxas/litebox-snp-novalidation-userptr) | 2026-10-12 | High local write primitive: LiteBox v0.1.0 SNP UserPtr is NoValidation |  |  |
