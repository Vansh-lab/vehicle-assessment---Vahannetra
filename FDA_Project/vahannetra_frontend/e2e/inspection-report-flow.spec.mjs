import { expect, test } from "@playwright/test";

const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=",
  "base64",
);

test("inspection and report flow", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Work Email").fill("ops@insurer.com");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByRole("button", { name: "Start New Inspection" }).click();
  await expect(page).toHaveURL(/\/inspection\/new$/);

  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("Plate Number").fill("MH12AB1234");
  await page.getByLabel("Vehicle Model").fill("Hyundai i20");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.locator('input[type="file"]').first().setInputFiles({
    name: "car.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });

  await page.getByRole("button", { name: "Analyze Damage" }).click();
  await expect(page).toHaveURL(/\/inspection\/result$/, { timeout: 30000 });

  await page.getByRole("button", { name: "Send to claim system" }).click();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Claim submitted:")).toBeVisible({ timeout: 10000 });
});
