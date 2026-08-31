import { type Page, expect, test } from "@playwright/test"
import { baseURL, firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { randomPassword } from "./utils/random.ts"

test.use({ storageState: { cookies: [], origins: [] } })

type OptionsType = {
  exact?: boolean
}

const fillForm = async (page: Page, email: string, password: string) => {
  await page.getByPlaceholder("Email").fill(email)
  await page.getByPlaceholder("Password", { exact: true }).fill(password)
}

const verifyInput = async (
  page: Page,
  placeholder: string,
  options?: OptionsType,
) => {
  const input = page.getByPlaceholder(placeholder, options)
  await expect(input).toBeVisible()
  await expect(input).toHaveText("")
  await expect(input).toBeEditable()
}

test("Inputs are visible, empty and editable", async ({ page }) => {
  await page.goto("/login")

  await verifyInput(page, "Email")
  await verifyInput(page, "Password", { exact: true })
})

test("Log In button is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(page.getByRole("button", { name: "Log In" })).toBeVisible()
})

test("Forgot Password link is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(
    page.getByRole("link", { name: "Forgot password?" }),
  ).toBeVisible()
})

test("Log in with valid email and password ", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()

  await page.waitForURL("/")

  await expect(
    page.getByText(/Welcome back/),
  ).toBeVisible()
})

test("Log in with invalid email", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, "invalidemail", firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()

  await expect(page.getByText("Invalid email address")).toBeVisible()
})

test("Log in with invalid password", async ({ page }) => {
  const password = randomPassword()

  await page.goto("/login")
  await fillForm(page, firstSuperuser, password)
  await page.getByRole("button", { name: "Log In" }).click()

  await expect(page.getByText("Incorrect email or password")).toBeVisible()
})

// Log out

test("Successful log out", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()

  await page.waitForURL("/")

  await expect(
    page.getByText(/Welcome back/),
  ).toBeVisible()

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL("/login")
})

test("Logged-out user cannot access protected routes", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()

  await page.waitForURL("/")

  await expect(
    page.getByText(/Welcome back/),
  ).toBeVisible()

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL("/login")

  await page.goto("/settings")
  await page.waitForURL("/login")
})

// A cookie the API no longer accepts (expired, or signed with a key that was
// rotated by a redeploy) used to strand the visitor: the nav rendered "Sign In"
// because /api/auth/me correctly 401s, but middleware saw the cookie and
// bounced /login straight back to "/", so the button looked broken and there
// was no way to sign in again short of clearing site data.
test("A stale session cookie still lets the user reach the login page", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "access_token",
      value: "stale.but.present",
      url: baseURL,
    },
  ])

  await page.goto("/login")

  await expect(page).toHaveURL(/\/login/)
  await verifyInput(page, "Email")
  await verifyInput(page, "Password", { exact: true })
})

test("A stale session cookie does not keep a protected route open", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "access_token",
      value: "stale.but.present",
      url: baseURL,
    },
  ])

  await page.goto("/settings")
  await page.waitForURL("/login")

  // The dead cookie is cleared on the way out, so nothing is left to bounce
  // the next request or to make the app look half signed-in.
  const cookies = await context.cookies()
  expect(cookies.find((c) => c.name === "access_token")?.value ?? "").toBe("")
})
