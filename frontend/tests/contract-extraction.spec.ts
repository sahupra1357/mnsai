import { type Page, expect, test } from "@playwright/test"

/** Frontend behaviour for the contract field-extraction workspace.
 *
 *  The four rules the schema calls out: the fixed five are locked on, the optional
 *  five toggle from none to all five, all ten keys render whatever was selected, and
 *  the failure banner appears whenever the status is `needs_verification`.
 *
 *  Every API call is stubbed, so this suite needs the Next.js app but no backend.
 *  The middleware only checks that an `access_token` cookie exists, so the fake one
 *  below is enough to reach the protected route. Run it with:
 *
 *      npx playwright test tests/contract-extraction.spec.ts --project=chromium --no-deps
 */

test.use({
  storageState: {
    cookies: [
      {
        name: "access_token",
        value: "playwright-stub-token",
        domain: "localhost",
        path: "/",
        expires: -1,
        httpOnly: true,
        secure: false,
        sameSite: "Lax",
      },
    ],
    origins: [],
  },
})

const CONTRACT_ROOT = "**/api/proxy/api/v1/contract-extractions"

const DEFAULT_KEYS = [
  "contract_title",
  "customer",
  "effective_date",
  "term_end_date",
  "contract_value",
]

const FIXED = [
  ["contract_title", "Contract title"],
  ["customer", "Customer"],
  ["effective_date", "Effective date"],
  ["term_end_date", "Term end date"],
  ["contract_value", "Contract value"],
] as const

const OPTIONAL = [
  ["governing_law", "Governing law"],
  ["payment_terms", "Payment terms"],
  ["notice_period", "Notice period"],
  ["renewal_terms", "Renewal terms"],
  ["termination_clause", "Termination clause"],
] as const

const CATALOGUE = {
  fields: [
    ...FIXED.map(([key, label]) => ({
      key,
      label,
      description: `${label} definition`,
      value_format: "verbatim",
      default_selected: true,
    })),
    ...OPTIONAL.map(([key, label]) => ({
      key,
      label,
      description: `${label} definition`,
      value_format: "verbatim",
      default_selected: false,
    })),
  ],
  default_fields: FIXED.map(([key]) => key),
}

function blankFields(): Record<string, string> {
  const fields: Record<string, string> = {}
  for (const [key] of [...FIXED, ...OPTIONAL]) fields[key] = ""
  return fields
}

async function stubApi(page: Page, result: Record<string, unknown>) {
  await page.route(`${CONTRACT_ROOT}/fields`, (route) =>
    route.fulfill({ json: CATALOGUE }),
  )
  await page.route(
    "**/api/proxy/api/v1/document-extractions/capabilities",
    (route) =>
      route.fulfill({
        json: {
          adapters: [],
          supported_extensions: [".pdf"],
          max_upload_bytes: 26214400,
          max_pages: 50,
          retry_limits: {},
          storage_provider: "local",
          execution_backend: "local",
          modal_enabled: false,
        },
      }),
  )
  // The source pane is not under test here; let it fall through to its download
  // fallback instead of reaching a real backend.
  await page.route("**/api/proxy/api/v1/document-extractions/*", (route) =>
    route.fulfill({ status: 404, json: { detail: "not found" } }),
  )
  await page.route(CONTRACT_ROOT, (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ json: result })
      : route.continue(),
  )
}

async function upload(page: Page, extractLabel: string) {
  await page
    .getByLabel("Choose a contract for field extraction")
    .setInputFiles({
      name: "contract.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 stub"),
    })
  await page.getByRole("button", { name: extractLabel }).click()
}

test("the five default fields start selected and can all be moved out", async ({
  page,
}) => {
  await stubApi(page, {})
  await page.goto("/contract-extraction")

  const selectedList = page.getByRole("listbox", {
    name: "Fields selected for extraction",
  })
  const availableList = page.getByRole("listbox", {
    name: "Available fields, not selected",
  })

  // Defaults: five on the right, five on the left.
  await expect(page.getByText("5 of 10 fields").first()).toBeVisible()
  await expect(selectedList.getByRole("option")).toHaveCount(5)
  await expect(availableList.getByRole("option")).toHaveCount(5)
  for (const [, label] of FIXED) {
    await expect(
      selectedList.getByRole("option", { name: new RegExp(label) }),
    ).toBeVisible()
  }

  // Nothing is locked: every default field can be pushed back to the left.
  await page.getByRole("button", { name: "Remove all fields" }).click()
  await expect(page.getByText("0 of 10 fields").first()).toBeVisible()
  await expect(selectedList.getByRole("option")).toHaveCount(0)
  await expect(availableList.getByRole("option")).toHaveCount(10)

  // With an empty right-hand list there is nothing to extract.
  await page
    .getByLabel("Choose a contract for field extraction")
    .setInputFiles({
      name: "contract.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 stub"),
    })
  await expect(
    page.getByRole("button", { name: "Select a field to extract" }),
  ).toBeDisabled()

  // One field is enough to proceed.
  await availableList.getByRole("option", { name: /Governing law/ }).dblclick()
  await expect(page.getByText("1 of 10 fields").first()).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Extract 1 field", exact: true }),
  ).toBeEnabled()
})

test("all ten fields move between the two lists, singly or as a whole set", async ({
  page,
}) => {
  await stubApi(page, {})
  await page.goto("/contract-extraction")

  const availableList = page.getByRole("listbox", {
    name: "Available fields, not selected",
  })
  const selectedList = page.getByRole("listbox", {
    name: "Fields selected for extraction",
  })

  // Whole set left to right — all ten, including the five that start selected.
  await page.getByRole("button", { name: "Add all fields" }).click()
  await expect(page.getByText("10 of 10 fields").first()).toBeVisible()
  await expect(availableList.getByRole("option")).toHaveCount(0)
  await expect(selectedList.getByRole("option")).toHaveCount(10)

  // Whole set back right to left — nothing is exempt.
  await page.getByRole("button", { name: "Remove all fields" }).click()
  await expect(page.getByText("0 of 10 fields").first()).toBeVisible()
  await expect(availableList.getByRole("option")).toHaveCount(10)
  await expect(selectedList.getByRole("option")).toHaveCount(0)

  // Highlight two and move just those.
  await availableList.getByRole("option", { name: /Contract title/ }).click()
  await availableList.getByRole("option", { name: /Governing law/ }).click()
  await page.getByRole("button", { name: "Add highlighted fields" }).click()
  await expect(page.getByText("2 of 10 fields").first()).toBeVisible()
  await expect(selectedList.getByRole("option")).toHaveCount(2)

  // Double-clicking a selected row sends it straight back.
  await selectedList.getByRole("option", { name: /Contract title/ }).dblclick()
  await expect(page.getByText("1 of 10 fields").first()).toBeVisible()
  await expect(availableList.getByRole("option")).toHaveCount(9)
})

test("all ten keys render even when no optional field was selected", async ({
  page,
}) => {
  await stubApi(page, {
    extraction_id: "11111111-1111-1111-1111-111111111111",
    document_id: "22222222-2222-2222-2222-222222222222",
    fields: {
      ...blankFields(),
      contract_title: "Master Services Agreement",
      customer: "Northwind Ltd",
      effective_date: "15/01/2026",
      term_end_date: "31/12/2026",
      contract_value: "USD 250000.00",
    },
    selected_fields: DEFAULT_KEYS,
    extraction_status: "complete",
    unresolved_fields: [],
    field_provenance: [],
    warnings: [],
    verified_values: {},
    created_at: "2026-08-27T10:00:00Z",
  })
  await page.goto("/contract-extraction")
  await upload(page, "Extract 5 fields")

  for (const [key] of [...FIXED, ...OPTIONAL]) {
    await expect(page.getByText(`"${key}"`, { exact: true })).toBeVisible()
  }
  // The unselected optional half is present, blank, and marked as such.
  await expect(page.getByText("not selected", { exact: true })).toHaveCount(5)
})

test("a blank requested field raises the non-dismissible failure banner", async ({
  page,
}) => {
  await stubApi(page, {
    extraction_id: "33333333-3333-3333-3333-333333333333",
    document_id: "44444444-4444-4444-4444-444444444444",
    fields: {
      ...blankFields(),
      contract_title: "Master Services Agreement",
      customer: "Northwind Ltd",
      effective_date: "15/01/2026",
      contract_value: "USD 250000.00",
    },
    selected_fields: DEFAULT_KEYS,
    extraction_status: "needs_verification",
    unresolved_fields: [
      { field_key: "term_end_date", reason: "not_found", detail: null },
    ],
    field_provenance: [],
    warnings: [],
    verified_values: {},
    created_at: "2026-08-27T10:00:00Z",
  })
  await page.goto("/contract-extraction")
  await upload(page, "Extract 5 fields")

  // The page carries more than one live region; target the status banner itself.
  const banner = page
    .getByRole("alert")
    .filter({ hasText: "human verification required" })
  await expect(banner).toContainText(
    "1 requested field could not be extracted — human verification required",
  )
  await expect(banner).toContainText("Term end date")
  await expect(banner.getByRole("button", { name: "Verify now" })).toBeVisible()
  // Not dismissible while the status is needs_verification.
  await expect(banner.getByRole("button", { name: "Dismiss" })).toHaveCount(0)

  await banner.getByRole("button", { name: "Verify now" }).click()
  await expect(
    page.getByRole("heading", { name: "Human verification" }),
  ).toBeVisible()
  await expect(page.getByLabel("Term end date", { exact: true })).toBeVisible()
})

test("a verified field shows the human value in the JSON, not the blank machine one", async ({
  page,
}) => {
  await stubApi(page, {
    extraction_id: "55555555-5555-5555-5555-555555555555",
    document_id: "66666666-6666-6666-6666-666666666666",
    fields: {
      ...blankFields(),
      contract_title: "MASTER",
      effective_date: "15/01/2026",
      term_end_date: "14/01/2027",
      contract_value: "USD 250000.00",
    },
    selected_fields: DEFAULT_KEYS,
    extraction_status: "verified",
    unresolved_fields: [
      { field_key: "customer", reason: "ungrounded", detail: null },
    ],
    field_provenance: [],
    warnings: [],
    // The machine column stays blank; the human's answer lives here.
    verified_values: { customer: "Northwind Ltd" },
    created_at: "2026-08-27T10:00:00Z",
  })
  await page.goto("/contract-extraction")
  await upload(page, "Extract 5 fields")

  const row = page.locator('[data-field="customer"]')
  await expect(row).toContainText('"Northwind Ltd"')
  await expect(row).toContainText("human verified")
  // The resolved field is no longer presented as a failure.
  await expect(row).not.toContainText("not extracted")
  await expect(row).not.toContainText("Could not be grounded")

  // Copy JSON must carry the same value the operator is looking at.
  const json = await page
    .getByLabel("Extracted contract fields as JSON")
    .innerText()
  expect(json).toContain("Northwind Ltd")

  // Provenance stays recoverable: both halves are shown side by side.
  await page.getByRole("button", { name: "View details" }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog.getByText("Human verification")).toBeVisible()
  await expect(dialog).toContainText("Northwind Ltd")
  await expect(dialog).toContainText("Machine value")
})
