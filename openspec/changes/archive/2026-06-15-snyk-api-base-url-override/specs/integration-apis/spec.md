## ADDED Requirements

### Requirement: Snyk REST API regional hosts

The default Snyk REST **Issues** base URL SHALL remain **`https://api.snyk.io/rest`** (**SNYK-US-01**). The integration SHALL support operator-configured **API origins** for other Snyk regions per **`application-config`**. Regional REST bases follow [Snyk REST API — API URLs](https://docs.snyk.io/developer-tools/snyk-api/rest-api/about-the-rest-api#api-urls):

| Region | API origin | REST base URL |
| ------ | ---------- | ------------- |
| SNYK-US-01 (default) | `https://api.snyk.io` | `https://api.snyk.io/rest` |
| SNYK-US-02 | `https://api.us.snyk.io` | `https://api.us.snyk.io/rest` |
| SNYK-EU-01 | `https://api.eu.snyk.io` | `https://api.eu.snyk.io/rest` |
| SNYK-AU-01 | `https://api.au.snyk.io` | `https://api.au.snyk.io/rest` |

Legacy **V1** API calls SHALL use **`{configured_origin}/v1`** with the same origin as REST. Normative Issues operations in this product use **REST**, not V1.

#### Scenario: Operator selects documented EU host

- **WHEN** effective **`api_base_url`** is **`https://api.eu.snyk.io`**
- **THEN** Issues list/get paths SHALL be issued against **`https://api.eu.snyk.io/rest`**

#### Scenario: Default host when origin omitted

- **WHEN** no layer supplies **`api_base_url`**
- **THEN** REST Issues operations SHALL use **`https://api.snyk.io/rest`**
