"use client"

import { useState, type ComponentType, type ElementType } from "react"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"

interface NavbarProps {
  type: string
  addModalAs: ComponentType<{ isOpen: boolean; onClose: () => void }> | ElementType
}

const Navbar = ({ type, addModalAs }: NavbarProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const AddModal = addModalAs as ComponentType<{ isOpen: boolean; onClose: () => void }>

  return (
    <div className="flex py-8 gap-4">
      <Button
        className="bg-ui-main hover:bg-[#003d8f] text-white gap-1 text-sm md:text-base"
        onClick={() => setIsOpen(true)}
      >
        <Plus size={16} /> Add {type}
      </Button>
      <AddModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </div>
  )
}

export default Navbar
