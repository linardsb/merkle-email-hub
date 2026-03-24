import { mergeTests } from "@playwright/test";
import { test as authTest } from "./auth";
import { test as apiTest } from "./api";

export const test = mergeTests(authTest, apiTest);
export { expect } from "@playwright/test";
