import { expect, test } from "@playwright/test";

test("workspace pages render key modules", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Fleet Health Score")).toBeVisible();
  await expect(page.getByRole("button", { name: "Start New Inspection" })).toBeVisible();

  await page.goto("/history");
  await expect(page).toHaveURL(/\/history$/);
  await expect(page.getByText("Inspection History")).toBeVisible();
  await expect(page.getByLabel("severity-filter")).toBeVisible();
  await expect(page.getByLabel("status-filter")).toBeVisible();
  await expect(page.getByLabel("date-filter")).toBeVisible();

  await page.locator('a[href^="/history/"]').first().click();
  await expect(page).toHaveURL(/\/history\/.+/);
  await expect(page.getByText("Detailed Report")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download PDF report" })).toBeVisible();

  await page.goto("/analytics");
  await expect(page).toHaveURL(/\/analytics$/);
  await expect(page.getByText("Severity Trends")).toBeVisible();
  await expect(page.getByText("Damage Distribution")).toBeVisible();
  await expect(page.getByText("Vehicle-wise Risk Ranking")).toBeVisible();

  await page.goto("/settings");
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByText("Organization Info")).toBeVisible();
  await expect(page.getByText("Notification Preferences")).toBeVisible();
  await expect(page.getByText("Backend Integration Status")).toBeVisible();
});
