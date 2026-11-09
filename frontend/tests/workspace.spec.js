import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

function credentials() {
  const text = fs.readFileSync(path.resolve('../backend/.initial-admin.txt'), 'utf8');
  return { username: text.match(/Username: (.+)/)[1], password: text.match(/Password: (.+)/)[1] };
}
async function signIn(page) {
  const { username, password } = credentials();
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in to PostMate' }).click();
  await expect(page.getByRole('heading', { name: /Good .*Admin/ })).toBeVisible();
}

test('document preview opens images and paginates PDFs with zoom controls', async ({ page }) => {
  // The API's real image/PDF rendering and permissions are tested against PostgreSQL.
  // This fixture isolates browser controls without creating private customer records.
  await page.route('**/api/documents/preview-fixture/preview?*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'image/png',
      headers: { 'X-Page-Count': '2' },
      body: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jTRkAAAAASUVORK5CYII=',
        'base64',
      ),
    }),
  );
  for (const format of ['pdf', 'image']) {
    await page.goto(`/tests/fixtures/document-preview.html?format=${format}`);
    const preview = page.getByRole('dialog');
    await expect(preview.getByRole('img', { name: /^AADHAAR/ })).toBeVisible();
    await expect(preview.getByRole('img', { name: /^AADHAAR/ })).toHaveJSProperty(
      'naturalWidth',
      1,
    );
    await preview.getByRole('button', { name: 'Zoom in', exact: true }).click();
    await expect(preview.getByText('125%', { exact: true })).toBeVisible();
    if (format === 'pdf') {
      await expect(preview.getByText('Page 1 of 2', { exact: true })).toBeVisible();
      await preview.getByRole('button', { name: 'Next', exact: true }).click();
      await expect(preview.getByText('Page 2 of 2', { exact: true })).toBeVisible();
      await preview.getByRole('button', { name: 'Previous', exact: true }).click();
      await expect(preview.getByText('Page 1 of 2', { exact: true })).toBeVisible();
    } else await expect(preview.getByRole('button', { name: 'Next', exact: true })).toHaveCount(0);
    await preview.getByRole('button', { name: 'Close dialog', exact: true }).click();
    await expect(page.getByText('Preview closed', { exact: true })).toBeVisible();
  }
});

test('account delete control is hidden for Staff and available for Super Admin', async ({
  page,
}) => {
  await page.goto('/tests/fixtures/account-maturity.html?role=staff');
  await expect(page.getByRole('button', { name: /^Edit account/ })).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Delete scheme account', exact: true }),
  ).toHaveCount(0);
  await page.goto('/tests/fixtures/account-maturity.html?role=super_admin');
  await expect(
    page.getByRole('button', { name: 'Delete scheme account', exact: true }),
  ).toBeVisible();
});

test('maturity amount and calendar lifespan are readable on desktop and mobile', async ({
  page,
}) => {
  for (const viewport of [
    { width: 900, height: 900 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/tests/fixtures/account-maturity.html');
    const card = page.locator('.profile-account-card');
    await expect(card.getByText('₹36,500.50', { exact: true })).toBeVisible();
    await expect(card.getByText('5 years, 0 months, 0 days', { exact: true })).toBeVisible();
    await expect(card.locator('.lifespan-remaining')).toBeVisible();
    await expect(card.locator('.lifespan-remaining')).toContainText(
      '2 years, 3 months, 3 days remaining',
    );
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/maturity-card-${viewport.width}.png`,
      fullPage: true,
    });
  }
});

test('desktop workspace, dynamic account fields, navigation and session logout', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await signIn(page);
  await expect(page.getByText('Workspace overview')).toBeVisible();
  await expect(
    page.locator('.topbar').getByRole('button', { name: 'Sign out', exact: true }),
  ).toBeVisible();
  await expect(
    page.locator('.sidebar').getByRole('button', { name: 'Sign out', exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText('Loading records…')).toHaveCount(0);
  await page.screenshot({ path: 'test-results/desktop-overview.png', fullPage: true });
  await page.getByRole('link', { name: 'Customers & schemes', exact: true }).click();
  await page.getByRole('button', { name: 'Add customer', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'Add customer & schemes' })).toBeVisible();
  await dialog.getByLabel('Full name').fill('Unsaved verification');
  await dialog.getByRole('button', { name: 'Create customer & schemes' }).click();
  await expect(dialog).toBeVisible();
  await expect(page.getByRole('link', { name: 'Scheme accounts', exact: true })).toHaveCount(0);
  await dialog.getByLabel('Savings scheme').selectOption({ label: 'PLI — Postal Life Insurance' });
  await expect(dialog.getByLabel('Policy number *', { exact: true })).toBeVisible();
  await dialog.getByLabel('Nominee name (optional)', { exact: true }).fill('Nominee entry check');
  await dialog.getByLabel('Maturity amount (INR, optional)', { exact: true }).fill('36000.50');
  await expect(dialog.getByLabel('Account number *', { exact: true })).toHaveCount(0);
  await dialog.getByLabel('Savings scheme').selectOption({ label: 'RD — Recurring Deposit' });
  await expect(dialog.getByLabel('Account number *', { exact: true })).toBeVisible();
  await expect(dialog.getByLabel('CIF ID *', { exact: true })).toBeVisible();
  await expect(dialog.getByLabel('Maturity amount (INR, optional)', { exact: true })).toHaveValue(
    '36000.50',
  );
  await expect(dialog.getByLabel('Nominee name (optional)', { exact: true })).toHaveValue(
    'Nominee entry check',
  );
  await dialog.getByRole('button', { name: 'Add another scheme' }).click();
  const second = dialog.getByRole('group', { name: 'Scheme 02', exact: true });
  await second.getByLabel('Savings scheme').selectOption({ label: 'PLI — Postal Life Insurance' });
  await expect(second.getByLabel('Policy number *', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/customer-registration.png', fullPage: true });
  const saveBounds = await dialog
    .getByRole('button', { name: 'Create customer & schemes' })
    .boundingBox();
  const modalBounds = await dialog.boundingBox();
  expect(saveBounds.y + saveBounds.height).toBeLessThanOrEqual(modalBounds.y + modalBounds.height);
  await dialog.getByRole('button', { name: 'Remove scheme 2' }).click();
  await dialog.getByRole('button', { name: 'Close dialog' }).click();
  await page.screenshot({ path: 'test-results/customer-workspace.png', fullPage: true });
  await page.getByRole('button', { name: /All scheme accounts/ }).click();
  await expect(page.getByLabel('Scheme filter')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open account', exact: true })).toHaveCount(0);
  for (const [link, heading] of [
    ['Payment dues', 'Payment dues'],
    ['Transactions', 'Transactions'],
    ['Reports', 'Reports'],
    ['Staff members', 'Staff members'],
    ['Scheme settings', 'Scheme settings'],
    ['Audit trail', 'Audit trail'],
  ]) {
    await page
      .getByRole('link', { name: new RegExp('^' + link) })
      .first()
      .click();
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
    await expect(page.getByRole('alert')).toHaveCount(0);
  }
  await page.getByRole('link', { name: 'Staff members', exact: true }).click();
  await page.getByRole('button', { name: 'Add staff', exact: true }).click();
  await expect(page.getByRole('dialog').getByText('Staff account', { exact: true })).toBeVisible();
  await expect(
    page.getByRole('dialog').getByRole('option', { name: 'Super Admin', exact: true }),
  ).toHaveCount(0);
  await page.getByRole('dialog').getByRole('button', { name: 'Close dialog' }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign in to PostMate' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('mobile layout and keyboard dialog dismissal', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await expect(page.getByText('Loading records…')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/mobile-overview.png', fullPage: true });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('link', { name: 'Customers & schemes', exact: true }).click();
  await page.getByRole('button', { name: 'Add customer', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.locator('.topbar').getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign in to PostMate' })).toBeVisible();
});

test('customer eye buttons reveal without a reason and deletion dialogs can be cancelled', async ({
  page,
}) => {
  await signIn(page);
  await page.getByRole('link', { name: 'Customers & schemes', exact: true }).click();
  await expect(page.getByText('Loading records…')).toHaveCount(0);
  const view = page.getByRole('button', { name: /^View / }).first();
  test.skip(
    (await view.count()) === 0,
    'No existing customer available for a read-only profile check',
  );
  const accountResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/accounts?customer_id=') && response.status() === 200,
  );
  await view.click();
  await accountResponse;
  const profile = page.getByRole('dialog');
  await expect(profile).toBeVisible();
  await expect(profile.getByText('Customer ID', { exact: true })).toHaveCount(0);
  const accountCard = profile.locator('.profile-account-card').first();
  if (await accountCard.count()) {
    await expect(accountCard.getByText('Maturity amount', { exact: true })).toBeVisible();
    if (await accountCard.locator('.account-lifespan').count()) {
      await expect(
        accountCard.getByText('Full term · opening to maturity', { exact: true }),
      ).toBeVisible();
    }
    await accountCard.getByRole('button', { name: /^Edit account / }).click();
    const accountEditor = page
      .getByRole('dialog')
      .filter({ has: page.getByRole('heading', { name: 'Update account details', exact: true }) });
    await expect(
      accountEditor.getByLabel('Maturity amount (INR, optional)', { exact: true }),
    ).toBeVisible();
    await accountEditor.getByRole('button', { name: 'Close dialog', exact: true }).click();
  }
  for (const kind of ['Aadhaar', 'PAN']) {
    const eye = profile.getByRole('button', { name: `Show ${kind} number`, exact: true });
    if (await eye.isEnabled()) {
      await eye.click();
      await expect(
        profile.getByRole('button', { name: `Hide ${kind} number`, exact: true }),
      ).toBeVisible();
      await expect(page.getByRole('dialog')).toHaveCount(1);
      await expect(profile.getByLabel('Reason (recorded in the audit trail)')).toHaveCount(0);
      await profile.getByRole('button', { name: `Hide ${kind} number`, exact: true }).click();
    }
  }
  const accountDelete = profile
    .getByRole('button', { name: 'Delete scheme account', exact: true })
    .first();
  if (await accountDelete.count()) {
    await accountDelete.click();
    const confirm = page
      .getByRole('dialog')
      .filter({ has: page.getByRole('heading', { name: 'Delete scheme account?', exact: true }) });
    await expect(
      confirm.getByRole('button', { name: 'Delete account', exact: true }),
    ).toBeVisible();
    await confirm.getByRole('button', { name: 'Cancel', exact: true }).click();
  }
  await profile.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page
    .getByRole('button', { name: /^Delete / })
    .first()
    .click();
  await expect(
    page.getByRole('dialog').getByRole('heading', { name: 'Delete customer?', exact: true }),
  ).toBeVisible();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.getByRole('link', { name: 'Transactions', exact: true }).click();
  await expect(page.getByLabel('Show deleted transactions')).toBeVisible();
  const deletePayment = page
    .getByRole('button', { name: 'Delete transaction', exact: true })
    .first();
  if (await deletePayment.count()) {
    await deletePayment.click();
    await expect(
      page.getByRole('dialog').getByRole('button', { name: 'Delete transaction', exact: true }),
    ).toBeVisible();
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
  }
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
});
