## When to Use

Use when the target has any endpoint that processes user-controlled input through an execution layer — template engines, shell commands, YAML/XML parsers, file paths used in operations, package resolution, or configuration files. RCE is the highest-payout vulnerability class because it grants direct execution control over target infrastructure. Every admin/management console, template/preview endpoint, upload processor, deserialization sink, and dependency resolver is a candidate. Highest-value targets: enterprise server products (GHES, self-hosted GitLab), supply chain/package registries, cloud-native infrastructure, and admin/management consoles.

