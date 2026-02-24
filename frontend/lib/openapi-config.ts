import { OpenAPI } from "@/src/client/core/OpenAPI"

export function initOpenAPI() {
  OpenAPI.BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  OpenAPI.TOKEN = undefined
  OpenAPI.WITH_CREDENTIALS = true
}
