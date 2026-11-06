## HackerOne Scope Retrieval
```bash
curl --max-time 30 --connect-timeout 10 -s "https://hackerone.com/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { team(handle: \"PROGRAM_HANDLE\") { name url policy_scopes(archived: false) { edges { node { asset_type asset_identifier eligible_for_bounty instruction } } } } }"}' \
  | jq '.data.team.policy_scopes.edges[].node'
```

