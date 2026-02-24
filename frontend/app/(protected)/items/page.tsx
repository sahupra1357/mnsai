"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, Suspense } from "react"
import { ItemsService } from "@/src/client"
import ActionsMenu from "@/components/common/actions-menu"
import Navbar from "@/components/common/navbar"
import AddItem from "@/components/items/add-item"
import { PaginationFooter } from "@/components/common/pagination-footer"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"

const PER_PAGE = 5

function getItemsQueryOptions({ page }: { page: number }) {
  return {
    queryFn: () =>
      ItemsService.readItems({ skip: (page - 1) * PER_PAGE, limit: PER_PAGE }),
    queryKey: ["items", { page }],
  }
}

function ItemsTable() {
  const queryClient = useQueryClient()
  const searchParams = useSearchParams()
  const router = useRouter()
  const page = Number(searchParams.get("page")) || 1

  const setPage = (newPage: number) => {
    router.push(`/items?page=${newPage}`)
  }

  const {
    data: items,
    isPending,
    isPlaceholderData,
  } = useQuery({
    ...getItemsQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
  })

  const hasNextPage = !isPlaceholderData && items?.data.length === PER_PAGE
  const hasPreviousPage = page > 1

  useEffect(() => {
    if (hasNextPage) {
      queryClient.prefetchQuery(getItemsQueryOptions({ page: page + 1 }))
    }
  }, [page, queryClient, hasNextPage])

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Title</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isPending ? (
            Array.from({ length: 3 }).map((_, index) => (
              <TableRow key={index}>
                {Array.from({ length: 4 }).map((_, i) => (
                  <TableCell key={i}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            items?.data.map((item) => (
              <TableRow
                key={item.id}
                className={isPlaceholderData ? "opacity-50" : ""}
              >
                <TableCell className="max-w-[150px] truncate">{item.id}</TableCell>
                <TableCell className="max-w-[150px] truncate">{item.title}</TableCell>
                <TableCell className="max-w-[150px] truncate text-muted-foreground">
                  {item.description || "N/A"}
                </TableCell>
                <TableCell>
                  <ActionsMenu type="Item" value={item} />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <PaginationFooter
        page={page}
        onChangePage={setPage}
        hasNextPage={hasNextPage}
        hasPreviousPage={hasPreviousPage}
      />
    </>
  )
}

export default function ItemsPage() {
  return (
    <div className="container mx-auto max-w-full">
      <h1 className="text-2xl font-semibold pt-12 text-center md:text-left">
        Items Management
      </h1>
      <Navbar type="Item" addModalAs={AddItem} />
      <Suspense>
        <ItemsTable />
      </Suspense>
    </div>
  )
}
