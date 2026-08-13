"use client"

import useAuth from "@/hooks/use-auth"
import Appearance from "@/components/user-settings/appearance"
import ChangePassword from "@/components/user-settings/change-password"
import DeleteAccount from "@/components/user-settings/delete-account"
import UserInformation from "@/components/user-settings/user-information"
import ProfilePhoto from "@/components/user-settings/profile-photo"
import ApiKeys from "@/components/user-settings/api-keys"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface SettingsTab {
  title: string
  component: React.ComponentType
  /** Rendered only for superusers. */
  superuserOnly?: boolean
  /** Hidden from superusers. */
  hideForSuperuser?: boolean
}

const tabsConfig: SettingsTab[] = [
  { title: "My profile", component: UserInformation },
  { title: "Password", component: ChangePassword },
  { title: "Appearance", component: Appearance },
  { title: "API keys", component: ApiKeys },
  // The public profile hero's headshot — only superusers own that page.
  { title: "Profile photo", component: ProfilePhoto, superuserOnly: true },
  // Superusers can't delete their own account.
  { title: "Danger zone", component: DeleteAccount, hideForSuperuser: true },
]

export default function SettingsPage() {
  // useAuth (a real query) rather than a one-shot cache read, so the tab list
  // settles once the current user resolves instead of on first paint.
  const { user: currentUser } = useAuth()
  const isSuperuser = Boolean(currentUser?.is_superuser)
  const finalTabs = tabsConfig.filter((tab) =>
    isSuperuser ? !tab.hideForSuperuser : !tab.superuserOnly,
  )

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">User Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your account details, security, and preferences.
        </p>
      </header>
      {/* Keyed by title, not index, so the selected tab survives the list
          changing when the current user resolves. */}
      <Tabs defaultValue={tabsConfig[0].title}>
        <TabsList className="h-auto flex-wrap justify-start">
          {finalTabs.map((tab) => (
            <TabsTrigger key={tab.title} value={tab.title}>
              {tab.title}
            </TabsTrigger>
          ))}
        </TabsList>
        {finalTabs.map((tab) => {
          const Component = tab.component
          return (
            <TabsContent
              key={tab.title}
              value={tab.title}
              className="mt-6 rounded-lg border border-border bg-card p-6"
            >
              <Component />
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}
