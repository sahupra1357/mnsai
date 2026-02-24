import { toast } from "sonner"
import { useCallback } from "react"

export function useToast() {
  const showToast = useCallback(
    (title: string, description: string, status: "success" | "error") => {
      if (status === "success") {
        toast.success(title, { description })
      } else {
        toast.error(title, { description })
      }
    },
    [],
  )

  return showToast
}

export default useToast
