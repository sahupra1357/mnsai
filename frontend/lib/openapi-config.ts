import axios from "axios"
import { OpenAPI } from "@/src/client/core/OpenAPI"
import { goToSubscription, quotaDetailFrom } from "@/lib/quota"

export function initOpenAPI() {
  OpenAPI.BASE = "/api/proxy"
  OpenAPI.TOKEN = undefined
  OpenAPI.WITH_CREDENTIALS = true

  // The generated client issues every call through the default axios instance,
  // so one interceptor covers all of it. A 402 means the account's lifetime
  // request quota is spent: send the user to the subscription page rather than
  // letting each caller surface its own confusing error.
  axios.interceptors.response.use(undefined, (error) => {
    if (error?.response?.status === 402) {
      const detail = quotaDetailFrom(error.response.data)
      if (detail) goToSubscription(detail)
    }
    return Promise.reject(error)
  })
}
