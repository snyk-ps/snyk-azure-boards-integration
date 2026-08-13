## ADDED Requirements

### Requirement: List work items by ids uses errorPolicy Omit for sync batch prefetch

For **List work items (by ids)**, the integration SHALL use:

`GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids}&errorPolicy=Omit&api-version=7.1`

**Purpose:** Fetch up to **200** work items in one GET. **`errorPolicy=Omit`** ensures missing or unreadable ids are omitted from the response instead of failing the entire request — required for **`sync`** batch prefetch when some mapping rows reference deleted work items.

**Documentation:** [Work Items - List](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/list?view=azure-devops-rest-7.1&tabs=HTTP).

#### Scenario: Batch list URL includes errorPolicy Omit

- **WHEN** **`sync`** or the Azure DevOps client builds a list-by-ids URL for batch prefetch
- **THEN** the URL SHALL include **`errorPolicy=Omit`**
