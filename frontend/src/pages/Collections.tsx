import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderKanban, Plus, Trash2 } from 'lucide-react'
import {
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorState,
  Input,
  Modal,
  Spinner,
} from '@/components/ui'
import { collectionsApi, documentsApi, extractErrorMessage } from '@/lib/api'
import { useToast } from '@/lib/toast'

export default function Collections() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const collections = useQuery({ queryKey: ['collections'], queryFn: collectionsApi.list })
  const documents = useQuery({
    queryKey: ['documents', 'all-for-collections'],
    queryFn: () => documentsApi.list({ limit: 200 }),
  })

  const create = useMutation({
    mutationFn: () => collectionsApi.create(name.trim(), description.trim() || undefined),
    onSuccess: () => {
      notify('Collection created.', 'success')
      setCreateOpen(false)
      setName('')
      setDescription('')
      queryClient.invalidateQueries({ queryKey: ['collections'] })
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => collectionsApi.remove(id),
    onSuccess: () => {
      notify('Collection deleted.', 'success')
      queryClient.invalidateQueries({ queryKey: ['collections'] })
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Collections</h1>
          <p className="mt-1 text-sm text-muted">
            Group documents into virtual folders. Collections only reference documents; they never
            duplicate file contents.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" /> New collection
        </Button>
      </header>

      {collections.isLoading ? (
        <Card>
          <Spinner label="Loading collections…" />
        </Card>
      ) : collections.isError ? (
        <Card>
          <ErrorState
            message={extractErrorMessage(collections.error)}
            onRetry={() => collections.refetch()}
          />
        </Card>
      ) : !collections.data || collections.data.items.length === 0 ? (
        <Card>
          <EmptyState
            icon={<FolderKanban className="h-8 w-8" />}
            title="No collections yet"
            description="Create a collection to keep related documents together."
            action={
              <Button size="sm" onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4" /> New collection
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {collections.data.items.map((collection) => (
            <Card key={collection.id}>
              <CardBody className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-sm font-semibold">{collection.name}</h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Delete ${collection.name}`}
                    onClick={() => remove.mutate(collection.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-danger" />
                  </Button>
                </div>
                <p className="text-xs text-muted">{collection.description || 'No description'}</p>
                <p className="text-[11px] text-muted">
                  {collection.document_count} document
                  {collection.document_count === 1 ? '' : 's'}
                </p>

                <details className="text-[11px]">
                  <summary className="cursor-pointer text-muted hover:text-foreground">
                    Manage documents
                  </summary>
                  <div className="mt-2 max-h-40 space-y-1 overflow-auto rounded-lg border border-border bg-background p-2">
                    {(documents.data?.items ?? []).map((document) => (
                      <label key={document.id} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="h-3 w-3"
                          onChange={(event) => {
                            if (event.target.checked) {
                              collectionsApi
                                .addDocuments(collection.id, [document.id])
                                .then(() =>
                                  queryClient.invalidateQueries({ queryKey: ['collections'] }),
                                )
                                .catch((error) => notify(extractErrorMessage(error), 'error'))
                            } else {
                              collectionsApi
                                .removeDocument(collection.id, document.id)
                                .then(() =>
                                  queryClient.invalidateQueries({ queryKey: ['collections'] }),
                                )
                                .catch((error) => notify(extractErrorMessage(error), 'error'))
                            }
                          }}
                        />
                        <span className="truncate">{document.filename}</span>
                      </label>
                    ))}
                    {(documents.data?.items ?? []).length === 0 && (
                      <p className="text-muted">No documents indexed yet.</p>
                    )}
                  </div>
                </details>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={createOpen}
        title="New collection"
        onClose={() => setCreateOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => create.mutate()} loading={create.isPending} disabled={!name.trim()}>
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label htmlFor="collection-name" className="mb-1.5 block text-xs font-medium text-muted">
              Name
            </label>
            <Input
              id="collection-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Research notes"
            />
          </div>
          <div>
            <label
              htmlFor="collection-description"
              className="mb-1.5 block text-xs font-medium text-muted"
            >
              Description (optional)
            </label>
            <Input
              id="collection-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
