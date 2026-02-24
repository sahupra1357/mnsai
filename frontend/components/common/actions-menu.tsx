"use client"

import { useState } from "react"
import { MoreVertical, Pencil, Trash2 } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import type { ItemPublic, UserPublic } from "@/src/client"
import EditUser from "@/components/admin/edit-user"
import EditItem from "@/components/items/edit-item"
import Delete from "./delete-alert"

interface ActionsMenuProps {
  type: string
  value: ItemPublic | UserPublic
  disabled?: boolean
}

const ActionsMenu = ({ type, value, disabled }: ActionsMenuProps) => {
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            disabled={disabled}
          >
            <MoreVertical size={16} />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem
            onClick={() => setEditOpen(true)}
            className="flex items-center gap-2"
          >
            <Pencil size={16} />
            Edit {type}
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => setDeleteOpen(true)}
            className="flex items-center gap-2 text-ui-danger focus:text-ui-danger"
          >
            <Trash2 size={16} />
            Delete {type}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {type === "User" ? (
        <EditUser
          user={value as UserPublic}
          isOpen={editOpen}
          onClose={() => setEditOpen(false)}
        />
      ) : (
        <EditItem
          item={value as ItemPublic}
          isOpen={editOpen}
          onClose={() => setEditOpen(false)}
        />
      )}
      <Delete
        type={type}
        id={value.id}
        isOpen={deleteOpen}
        onClose={() => setDeleteOpen(false)}
      />
    </>
  )
}

export default ActionsMenu
