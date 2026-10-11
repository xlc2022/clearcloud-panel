// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FieldInput, initialValue } from "./IntegrationForm";
import type { FieldSpec } from "../types";

afterEach(cleanup);

const base: FieldSpec = { key: "token", label: "Token", type: "secret", required: true, default: null, help: "Long-lived token.", placeholder: null, options: null };

describe("FieldInput", () => {
  it("shows the keep-stored placeholder for a saved secret and never a value", () => {
    render(<FieldInput field={base} value="" secretSet onChange={() => {}} />);
    const input = screen.getByLabelText(/Token/) as HTMLInputElement;
    expect(input.placeholder).toBe("Saved, leave blank to keep");
    expect(input.value).toBe("");
    expect(input.required).toBe(false);
    expect(screen.getByText("Long-lived token.")).toBeTruthy();
  });

  it("renders select options and reports changes", () => {
    const onChange = vi.fn();
    const f: FieldSpec = { ...base, key: "mode", label: "Mode", type: "select", options: [{ value: "a", label: "Alpha" }, { value: "b", label: "Beta" }] };
    render(<FieldInput field={f} value="a" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Mode"), { target: { value: "b" } });
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("uses defaults for initial values", () => {
    expect(initialValue({ ...base, type: "bool", default: true }, undefined)).toBe(true);
    expect(initialValue({ ...base, type: "number", default: 8123 }, undefined)).toBe("8123");
    expect(initialValue({ ...base, type: "text", default: "x" }, "y")).toBe("y");
  });
});
