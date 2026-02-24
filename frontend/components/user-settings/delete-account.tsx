"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import DeleteConfirmation from "./delete-confirmation"

const DeleteAccount = () => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="max-w-full">
      <h3 className="text-sm font-semibold py-4">Delete Account</h3>
      <p className="text-sm text-muted-foreground">
        Permanently delete your data and everything associated with your account.
      </p>
      <Button
        variant="destructive"
        className="mt-4"
        onClick={() => setIsOpen(true)}
      >
        Delete
      </Button>
      <DeleteConfirmation
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </div>
  )
}

export default DeleteAccount
