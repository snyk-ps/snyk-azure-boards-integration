## ADDED Requirements

### Requirement: create_only_when_fix_available gate evaluates all coordinates

When merged **`create_only_when_fix_available`** is **`true`** for the active routing context, **`sync`** SHALL determine fix availability for an issue by examining **every** **`coordinates[]`** entry on the working issue view (after **GET** enrichment per **P2-FR-5.1** where applicable).

An issue SHALL satisfy the fix-available policy when **at least one** **`coordinates[]`** entry has **at least one** of the following boolean fields set to **`true`**: **`is_upgradeable`**, **`is_patchable`**, **`is_fixable_manually`**, **`is_fixable_snyk`**, **`is_fixable_upstream`**. **`is_pinnable`** SHALL NOT satisfy the policy.

The implementation SHALL NOT restrict evaluation to the first **`coordinates[]`** entry. Entries that are not objects SHALL be skipped without failing the run. When **`coordinates`** is absent, is not a list, or is empty, the issue SHALL NOT satisfy the policy.

This policy SHALL be applied consistently at every create gate that references **`create_only_when_fix_available`**: unmapped creation, recreation when a mapped work item id is missing, reopen creation, and routing-migration recreation.

When merged **`create_only_when_fix_available`** is **`false`**, this policy SHALL NOT gate creation.

#### Scenario: Fix signal on a later coordinate qualifies

- **WHEN** **`create_only_when_fix_available`** is **`true`**, the first **`coordinates[]`** entry has all recognized signals **`false`**, and a later entry has **`is_upgradeable`** **`true`**
- **THEN** the issue SHALL satisfy the fix-available policy and SHALL be eligible for work item creation

#### Scenario: No coordinate carries a signal

- **WHEN** **`create_only_when_fix_available`** is **`true`** and no **`coordinates[]`** entry has any recognized signal **`true`**
- **THEN** the issue SHALL NOT satisfy the policy and **`sync`** SHALL skip creation for that issue without failing the run

#### Scenario: Pinnable alone does not qualify

- **WHEN** **`create_only_when_fix_available`** is **`true`** and the only **`true`** signal on any coordinate is **`is_pinnable`**
- **THEN** the issue SHALL NOT satisfy the fix-available policy

#### Scenario: Absent coordinates does not qualify

- **WHEN** **`create_only_when_fix_available`** is **`true`** and the working issue view has no **`coordinates`**, a non-list **`coordinates`**, or an empty list
- **THEN** the issue SHALL NOT satisfy the fix-available policy

#### Scenario: Malformed coordinate entries do not fail the run

- **WHEN** **`coordinates[]`** contains a non-object entry alongside an object entry with **`is_patchable`** **`true`**
- **THEN** **`sync`** SHALL skip the non-object entry, SHALL treat the issue as satisfying the policy, and SHALL NOT raise

#### Scenario: Gate disabled ignores fix signals

- **WHEN** merged **`create_only_when_fix_available`** is **`false`**
- **THEN** **`sync`** SHALL NOT skip creation on fix-availability grounds regardless of **`coordinates[]`** content

---

### Requirement: Issues skipped for fix availability persist no mapping decision

When **`sync`** skips an issue solely because it does not satisfy the fix-available policy, the run SHALL NOT write a mapping row for that issue and SHALL NOT persist any state recording the skip. The issue SHALL remain **unmapped** for subsequent runs.

Snyk Issues list filtering SHALL NOT apply a server-side fix-availability predicate, so a skipped issue SHALL continue to be returned by subsequent list operations while it otherwise qualifies for the run's severity, status, origin, and time-bound filters.

Consequently, when a later run evaluates the same issue and the fix-available policy is satisfied, **`sync`** SHALL create the work item through the ordinary unmapped-create path and SHALL upsert the mapping row with the resulting **`work_item_id`** in that same run, without any backfill or replay step.

#### Scenario: Skipped issue writes no mapping row

- **WHEN** **`create_only_when_fix_available`** is **`true`** and an issue fails the fix-available policy
- **THEN** **`sync`** SHALL skip Azure DevOps mutation for that issue and the issues sync persistence SHALL contain no row for that issue arising from this run

#### Scenario: Previously skipped issue is created on a later run

- **WHEN** an issue was skipped on an earlier run for fix availability, satisfies the policy on a later run, derived status is **`open`**, and the remaining create gates pass
- **THEN** that later run SHALL create a work item for the issue and SHALL upsert the mapping row with the new **`work_item_id`** and **`work_item_status`**

## MODIFIED Requirements

### Requirement: P2-FR-5.5 fix availability and fix guidance

The application SHALL read boolean fix signals from each **`coordinates[]`** object: **`is_upgradeable`**, **`is_patchable`**, **`is_fixable_manually`**, **`is_fixable_snyk`**, **`is_fixable_upstream`**. The human-readable fix-availability summary SHALL be derived from the **union** of signals that are **`true`** across **all** **`coordinates[]`** entries, not from the first entry alone. Each label SHALL appear at most once, and label ordering SHALL be stable across runs for the same input.

The work item description SHALL **not** surface **`is_pinnable`** in the human-readable fix-availability summary (low signal for typical developer workflows).

The work item description SHALL summarize **true** flags using **human-readable** labels (not raw field names) together with the issue **title** and the **primary package** line from **P2-FR-5.1** where applicable.

When **`coordinates[].remedies`** or other structured fix guidance is present on the issue payload (including after **GET** enrichment per **P2-FR-5.1**), the work item description SHALL include that guidance in human-readable form. When structured fields carry **recommended upgrade** or **target version** identifiers (**`upgradeTo`**, **`changes[].upgradeTo`**, or dependency version hints documented in **`design.md`**), the description SHALL surface those as explicit **upgrade / fix version** guidance when available.

#### Scenario: Summary omits is_pinnable

- **WHEN** only **`is_pinnable`** is true among fix signals
- **THEN** the human-readable fix-availability line SHALL NOT imply a meaningful automated upgrade path solely from pin semantics (implementation MAY omit **`is_pinnable`** from the displayed summary)

#### Scenario: Summary unions signals across coordinates

- **WHEN** one **`coordinates[]`** entry has **`is_patchable`** **`true`** and a different entry has **`is_upgradeable`** **`true`**
- **THEN** the fix-availability summary SHALL include labels for both signals, each listed once

#### Scenario: Summary uses signal from a later coordinate

- **WHEN** the first **`coordinates[]`** entry has no **`true`** fix signals and a later entry has **`is_fixable_snyk`** **`true`**
- **THEN** the fix-availability summary SHALL include the label for that signal

#### Scenario: Remedies rendered when coordinates contain remedies

- **WHEN** **`coordinates[].remedies`** is present after list and GET merge
- **THEN** the work item description SHALL include formatted remedy guidance
