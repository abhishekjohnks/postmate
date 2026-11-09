import { test, expect } from '@playwright/test';

test('day/month/year input validates calendar dates and preserves ISO API values', async ({
  page,
}) => {
  await page.goto('/tests/fixtures/date-input.html');
  const input = page.getByRole('textbox', { name: 'Date', exact: true });
  await expect(input).toHaveValue('29/02/2024');
  const calendar = page.getByLabel('Choose date from calendar');
  await expect(calendar).toHaveAttribute('type', 'date');
  await calendar.fill('2026-11-05');
  await expect(input).toHaveValue('05/11/2026');
  await expect(page.locator('output')).toHaveText('2026-11-05');
  await input.fill('04/11/2026');
  await expect(page.locator('output')).toHaveText('2026-11-04');
  for (const invalid of ['31/02/2026', '02/29/2024', '01/01/2031', '01/01/2019']) {
    await input.fill(invalid);
    expect(await input.evaluate((el) => el.checkValidity())).toBe(false);
    await expect(page.locator('output')).toHaveText('2026-11-04');
  }
  await input.fill('29/02/2028');
  expect(await input.evaluate((el) => el.checkValidity())).toBe(true);
  await expect(page.locator('output')).toHaveText('2028-02-29');
  await input.fill('');
  await expect(page.locator('output')).toHaveText('');
  expect(await input.evaluate((el) => el.checkValidity())).toBe(false);
});
