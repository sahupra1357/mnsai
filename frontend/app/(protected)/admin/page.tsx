"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, Suspense } from "react"
import { UsersService } from "@/src/client"
import AddUser from "@/components/admin/add-user"
import ActionsMenu from "@/components/common/actions-menu"
import Navbar from "@/components/common/navbar"
import { PaginationFooter } from "@/components/common/pagination-footer"
import useAuth from "@/hooks/use-auth"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const PER_PAGE = 5

function getUsersQueryOptions({ page }: { page: number }) {
  return {
    queryFn: () =>
      UsersService.readUsers({ skip: (page - 1) * PER_PAGE, limit: PER_PAGE }),
    queryKey: ["users", { page }],
  }
}

function UsersTable() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const searchParams = useSearchParams()
  const router = useRouter()
  const page = Number(searchParams.get("page")) || 1

  const setPage = (newPage: number) => {
    router.push(`/admin?page=${newPage}`)
  }

  const {
    data: users,
    isPending,
    isPlaceholderData,
  } = useQuery({
    ...getUsersQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
  })

  const hasNextPage = !isPlaceholderData && users?.data.length === PER_PAGE
  const hasPreviousPage = page > 1

  useEffect(() => {
    if (hasNextPage) {
      queryClient.prefetchQuery(getUsersQueryOptions({ page: page + 1 }))
    }
  }, [page, queryClient, hasNextPage])

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-1/5">Full name</TableHead>
            <TableHead className="w-1/2">Email</TableHead>
            <TableHead className="w-[10%]">Role</TableHead>
            <TableHead className="w-[10%]">Requests</TableHead>
            <TableHead className="w-[10%]">Status</TableHead>
            <TableHead className="w-[10%]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isPending ? (
            Array.from({ length: 3 }).map((_, index) => (
              <TableRow key={index}>
                {Array.from({ length: 6 }).map((_, i) => (
                  <TableCell key={i}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            users?.data.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="max-w-[150px] truncate text-muted-foreground">
                  {user.full_name || "N/A"}
                  {currentUser?.id === user.id && (
                    <Badge className="ml-1 bg-teal-500 text-white">You</Badge>
                  )}
                </TableCell>
                <TableCell className="max-w-[150px] truncate">
                  {user.email}
                </TableCell>
                <TableCell>{user.is_superuser ? "Superuser" : "User"}</TableCell>
                <TableCell>
                  {user.is_superuser ? (
                    <span className="text-muted-foreground">Unlimited</span>
                  ) : (
                    <span
                      className={
                        user.request_count >= user.request_limit
                          ? "text-ui-danger font-medium"
                          : ""
                      }
                    >
                      {user.request_count} / {user.request_limit}
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${user.is_active ? "bg-ui-success" : "bg-ui-danger"}`}
                    />
                    {user.is_active ? "Active" : "Inactive"}
                  </div>
                </TableCell>
                <TableCell>
                  <ActionsMenu
                    type="User"
                    value={user}
                    disabled={currentUser?.id === user.id}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <PaginationFooter
        onChangePage={setPage}
        page={page}
        hasNextPage={hasNextPage}
        hasPreviousPage={hasPreviousPage}
      />
    </>
  )
}

export default function AdminPage() {
  const { user, isLoading } = useAuth()

  // Every /users endpoint behind this page requires a superuser, so a plain
  // signed-in user gets the same refusal here that the API would give.
  if (isLoading) {
    return (
      <div className="container mx-auto max-w-full pt-12">
        <Skeleton className="h-8 w-48" />
      </div>
    )
  }

  if (!user?.is_superuser) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-muted-foreground text-sm">
        Access denied. Superuser required.
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-full">
      <h1 className="text-2xl font-semibold pt-12 text-center md:text-left">
        Users Management
      </h1>
      <Navbar type="User" addModalAs={AddUser} />
      <Suspense>
        <UsersTable />
      </Suspense>
    </div>
  )
}
