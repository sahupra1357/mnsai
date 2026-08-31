import path from "node:path"
import dotenv from "dotenv"

// Resolved from the working directory rather than `import.meta.url`: that is an
// ESM-only construct, and Playwright loads these files as CommonJS, which on
// Node 22 fails the whole suite with "Cannot require() ES Module". Playwright
// runs with the config's directory (frontend/) as cwd, so the repo-root .env is
// one level up.
dotenv.config({ path: path.resolve(process.cwd(), "../.env") })

const { FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD } = process.env

if (typeof FIRST_SUPERUSER !== "string") {
  throw new Error("Environment variable FIRST_SUPERUSER is undefined")
}

if (typeof FIRST_SUPERUSER_PASSWORD !== "string") {
  throw new Error("Environment variable FIRST_SUPERUSER_PASSWORD is undefined")
}

/** Where the suite points. Defaults to the usual dev port; override to run
 *  against an instance on another port (e.g. a second dev server). */
export const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000"

export const firstSuperuser = FIRST_SUPERUSER as string
export const firstSuperuserPassword = FIRST_SUPERUSER_PASSWORD as string
