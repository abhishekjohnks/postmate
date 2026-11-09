import { test, expect } from '@playwright/test';

test('customer card shows deposits and records a direct payment with calendar date', async ({
  page,
}) => {
  await page.route('**/api/schedules?*', (route) => route.fulfill({ json: { items: [] } }));
  let submitted;
  await page.route('**/api/payments/flexible', async (route) => {
    submitted = route.request().postDataJSON();
    expect(route.request().headers()['idempotency-key']).toBeTruthy();
    await route.fulfill({
      status: 201,
      json: {
        customer_name: 'Example customer',
        amount: submitted.amount,
        payment_date: submitted.payment_date,
        receipt_id: 'example-receipt',
      },
    });
  });
  await page.goto('/tests/fixtures/direct-deposit.html');
  await expect(page.getByText('Total deposited', { exact: true })).toBeVisible();
  await expect(page.getByText(/600\.00/)).toBeVisible();
  await expect(page.getByText(/Annual shortfall:/)).toBeVisible();
  await page.getByRole('button', { name: 'Record deposit', exact: true }).click();
  const modal = page.getByRole('dialog');
  await modal.getByLabel('Amount received (INR)').fill('500');
  await modal.getByLabel('Choose date from calendar').fill('2026-11-05');
  await expect(modal.getByLabel('Actual payment date', { exact: true })).toHaveValue('05/11/2026');
  await modal.getByRole('button', { name: 'Save payment & create receipt' }).click();
  await expect(modal.getByRole('button', { name: 'Download PDF receipt' })).toBeVisible();
  expect(submitted.account_id).toBe('test-flexible');
  expect(submitted.payment_date).toBe('2026-11-05');
  expect(submitted.amount).toBe('500');
  expect(submitted.schedule_id).toBeUndefined();
});
