import WithSubnavigation from "@/components/common/with-subnavigation"

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <WithSubnavigation />
      <main>{children}</main>
    </>
  )
}
