"use client"

import { useQueryClient } from "@tanstack/react-query"
import type { UserPublic } from "@/src/client"
import Appearance from "@/components/user-settings/appearance"
import ChangePassword from "@/components/user-settings/change-password"
import DeleteAccount from "@/components/user-settings/delete-account"
import UserInformation from "@/components/user-settings/user-information"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

const tabsConfig = [
  { title: "My profile", component: UserInformation },
  { title: "Password", component: ChangePassword },
  { title: "Appearance", component: Appearance },
  { title: "Danger zone", component: DeleteAccount },
]

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const currentUser = queryClient.getQueryData<UserPublic>(["currentUser"])
  const finalTabs = currentUser?.is_superuser
    ? tabsConfig.slice(0, 3)
    : tabsConfig

  return (
    <div className="container mx-auto max-w-full">
      <h1 className="text-2xl font-semibold py-12 text-center md:text-left">
        User Settings
      </h1>
      <Tabs defaultValue="0">
        <TabsList>
          {finalTabs.map((tab, index) => (
            <TabsTrigger key={index} value={String(index)}>
              {tab.title}
            </TabsTrigger>
          ))}
        </TabsList>
        {finalTabs.map((tab, index) => {
          const Component = tab.component
          return (
            <TabsContent key={index} value={String(index)}>
              <Component />
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}
