## MODIFIED Requirements

### Requirement: Azure Boards defaults — optional area path

The loader SHALL accept an optional **`area_path`** string under **`azure_boards.defaults`**, holding a full Azure DevOps area path (for example **`MyProject\\TeamA`** or **`MyProject\\Area\\SubArea`**). When omitted or whitespace-only after trim, no default area path is configured at this layer.

The loader SHALL reject a non-string value for **`area_path`**. The loader SHALL **not** accept **`area_path`** as a direct child of **`azure_boards`**; it belongs only under **`azure_boards.defaults`**.

**`CONFIGURATION.md`**, **`README.md`**, and the tracked sample YAML under **`data/`** SHALL document **`area_path`** as the YAML fallback when no **`repo-mapping.csv`** row matches, and SHALL document that **`org_mappings[].overrides.area_path`** overrides this default for that mapping row.

**`CONFIGURATION.md`** and **`README.md`** SHALL also document that when a **`repo-mapping.csv`** row matches, per-repo ADO **organization** and **project** (from **Area Path**) override the YAML **`organization`** / **`project`** for that issue only, while **`config.yaml`** **`org_mappings`** remains one Snyk org per row (1:1 baseline).

#### Scenario: Omitted area path defaults to unset at YAML layer

- **WHEN** YAML omits **`azure_boards.defaults.area_path`**
- **THEN** loading SHALL succeed and no default area path is configured unless a CSV row or org override supplies one

#### Scenario: Explicit default area path loads

- **WHEN** YAML sets **`area_path: MyProject\\TeamA`** under **`defaults`**
- **THEN** loading SHALL succeed and merged configuration SHALL expose that value for sync fallback resolution

#### Scenario: Flat area_path under azure_boards rejected

- **WHEN** YAML sets **`azure_boards.area_path`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.defaults.area_path`**

---

### Requirement: Azure Boards repo_mapping_csv path

Under **`azure_boards`**, the configuration MAY include **`repo_mapping_csv`**, a non-secret string path to the operator **`repo-mapping.csv`** file. When omitted at all precedence layers, the effective default SHALL be **`repo-mapping.csv`** resolved in the directory containing the loaded YAML configuration file (see **`repo-area-path-mapping`**).

The implementation SHALL recognize environment variable **`REPO_MAPPING_CSV_PATH`** with the same semantics, participating in **defaults → YAML → environment → CLI** precedence.

The loader SHALL reject a non-string **`repo_mapping_csv`** value.

**`CONFIGURATION.md`** and **`README.md`** SHALL document **`repo_mapping_csv`**, **`REPO_MAPPING_CSV_PATH`**, the default filename **`repo-mapping.csv`**, Azure Files co-location beside operator YAML, and the updated CSV column set (**`ADO Organization`**, full **`Project\\Area`** **Area Path**, **`Assignee (Optional)`**). Documentation SHALL note that **`AZURE_DEVOPS_PAT`** must authorize every ADO organization and project listed in the CSV.

#### Scenario: repo_mapping_csv relative path resolves beside config

- **WHEN** YAML is loaded from **`/config/config.yaml`** and sets **`repo_mapping_csv: custom.csv`**
- **THEN** the effective path SHALL be **`/config/custom.csv`**

#### Scenario: REPO_MAPPING_CSV_PATH overrides YAML

- **WHEN** YAML sets **`repo_mapping_csv`** and **`REPO_MAPPING_CSV_PATH`** is set in the environment
- **THEN** the effective path SHALL be the environment value

---

## ADDED Requirements

### Requirement: Repo mapping CSV operator documentation in application config

**`CONFIGURATION.md`** SHALL document the breaking CSV migration from prior formats: operators MUST add **`ADO Organization`** (non-empty per row) and MUST use full **`Project\\Area`** values in **Area Path**. Documentation SHALL explain that **`GitHub Org/ADO Project`** remains the Snyk-side match key, not the ADO routing destination.

**`README.md`** Deployment section SHALL reference multi-project routing within one Snyk org via **`repo-mapping.csv`** without adding duplicate **`org_mappings`** rows.

#### Scenario: CONFIGURATION documents CSV migration

- **WHEN** an operator reads **`CONFIGURATION.md`**
- **THEN** they SHALL find migration guidance for **`ADO Organization`** and full **Area Path** format

#### Scenario: README documents one Snyk org multi-project pattern

- **WHEN** an operator reads **`README.md`**
- **THEN** they SHALL find that one **`org_mappings`** row plus **`repo-mapping.csv`** can route repos to multiple ADO projects
