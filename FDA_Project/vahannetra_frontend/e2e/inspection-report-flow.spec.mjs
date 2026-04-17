import { expect, test } from "@playwright/test";

const tinyPngBase64 =
  "iVBORw0KGgoAAAANSUhEUgAAAZAAAADwCAIAAAAnqfEgAAABvUlEQVR4nO3UQQ0AIBDAMMC/58MCP7KkVbDX1pk5A6Dq2wG8yQwQIAABAgQIECBAgAABAgQIECBAgAABAgQIECBAgAABAgQIECBA4M0K8Hf9b7s4cP7R7xgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAj8WQX4u/5f3xw4/2j3DAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECf1YB/q7/1zcHzj/aPQMCBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAwJ8V4O/6f31z4Pyj3TMgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECfxZBfi7/l/fHDj/aPcMCBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQJ/VgH+rv/XNwfOP9o9AwIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIDAnxXg7/p/fXPg/KPdMyBAgAABAgQIECBAgAABAgQIECBAgAABAgQIECBAgAABAgQJ/AEsSwJf1ATY8QAAAABJRU5ErkJggg==";

test("inspection and report flow", async ({ page }) => {
  await page.goto("/inspection/new");
  await expect(page).toHaveURL(/\/inspection\/new$/);
  await page.getByRole("button", { name: "Continue" }).click();

  await page.fill("#plate", "MH12AB9087");
  await page.fill("#model", "Hyundai i20");
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Rear" }).click();
  await page.getByRole("button", { name: "Left" }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.locator('input[type="file"]').last().setInputFiles({
    name: "test.png",
    mimeType: "image/png",
    buffer: Buffer.from(tinyPngBase64, "base64"),
  });
  await expect(page.getByAltText("inspection preview")).toBeVisible();

  await page.getByRole("button", { name: "Analyze Damage" }).click();
  await expect(page).toHaveURL(/\/inspection\/result$/, { timeout: 30000 });
  await expect(page.getByText("Vehicle Summary")).toBeVisible();

  await page.getByRole("button", { name: "Send to claim system" }).click({ force: true });
  await expect(page.getByText("Claim submitted:")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download report" })).toBeVisible();
});
