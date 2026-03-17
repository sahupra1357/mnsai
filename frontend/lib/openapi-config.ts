import { OpenAPI } from "@/src/client/core/OpenAPI"

export function initOpenAPI() {
  OpenAPI.BASE = "/api/proxy"
  OpenAPI.TOKEN = undefined
  OpenAPI.WITH_CREDENTIALS = true
}
