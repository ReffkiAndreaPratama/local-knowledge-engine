import { expect, test } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const sampleDocument = fileURLToPath(
  new URL('../../sample_documents/atlas-onboarding.txt', import.meta.url),
)

test.describe('import → search → open source → delete', () => {
  test('indexes a sample document and removes it again', async ({ page }) => {
    await page.goto('/documents')

    // Import the synthetic onboarding guide through the real file input.
    await page
      .getByLabel('Choose files to import')
      .setInputFiles(sampleDocument)

    await expect(page.getByText(/file\(s\) queued/)).toBeVisible()

    const documentRow = page.getByRole('row', { name: /atlas-onboarding\.txt/ })
    await expect(documentRow).toBeVisible()
    await expect(documentRow.getByText('completed')).toBeVisible({ timeout: 60_000 })

    // Search for a term that only exists in the imported document.
    await page.getByLabel('Global search').fill('Project Halyard')
    await page.getByLabel('Global search').press('Enter')

    await expect(page).toHaveURL(/\/search\?q=Project(%20|\+)Halyard/)
    const result = page.getByRole('button', { name: /atlas-onboarding\.txt/ })
    await expect(result).toBeVisible()
    await expect(result).toContainText('Halyard')

    // Opening the result must show verifiable source context.
    await result.click()
    const preview = page.getByRole('complementary', { name: 'Source preview' })
    await expect(preview).toBeVisible()
    await expect(preview).toContainText('atlas-onboarding.txt')
    await expect(preview).toContainText('Halyard')
    await expect(preview).toContainText(/chunk: [0-9a-f-]{36}/)

    // Delete the document and confirm it disappears from the index.
    await page.getByRole('link', { name: 'Documents' }).click()
    const rowToDelete = page.getByRole('row', { name: /atlas-onboarding\.txt/ })
    await rowToDelete
      .getByRole('button', { name: 'Delete atlas-onboarding.txt' })
      .click()

    const dialog = page.getByRole('dialog', { name: 'Remove document' })
    await expect(dialog).toContainText('cannot be undone')
    await dialog.getByRole('button', { name: 'Delete permanently' }).click()

    await expect(page.getByRole('row', { name: /atlas-onboarding\.txt/ })).toHaveCount(0)

    // A hard reload bypasses the query cache and checks the backend state.
    await page.goto('/search?q=Project%20Halyard')
    await expect(page.getByText('No matching passages')).toBeVisible()
  })
})
