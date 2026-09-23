import { describe, expect, it } from "vitest";

import { initials } from "../src/dashboard/StaffList";

describe("initials", () => {
  it("uses the first two characters of a single-word name", () => {
    expect(initials("Ramesh")).toBe("RA");
    expect(initials("Meena")).toBe("ME");
  });

  it("uses the first and last word's initial for a multi-word name", () => {
    expect(initials("Dr. Rao")).toBe("DR");
    expect(initials("Mary Jane Watson")).toBe("MW");
  });

  it("collapses repeated whitespace and trims the name", () => {
    expect(initials("  Mary   Jane  ")).toBe("MJ");
  });

  it("returns an empty string for an empty or whitespace-only name", () => {
    expect(initials("")).toBe("");
    expect(initials("   ")).toBe("");
  });

  it("uppercases the result", () => {
    expect(initials("ramesh")).toBe("RA");
    expect(initials("mary jane")).toBe("MJ");
  });
});
