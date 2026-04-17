import { expect, test } from "@playwright/test";

test("inspection and report flow", async ({ page }) => {
  await page.goto("/inspection/new");
  await expect(page).toHaveURL(/\/inspection\/new$/);
  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();

  await page.goto("/inspection/result");
  await expect(page).toHaveURL(/\/inspection\/result$/);

  await page.getByRole("button", { name: "Send to claim system" }).click({ force: true });
  await expect(page.getByRole("button", { name: "Download report" })).toBeVisible();
});
