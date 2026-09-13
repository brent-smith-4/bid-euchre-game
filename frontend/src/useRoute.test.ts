import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useRoute } from "./useRoute";

describe("useRoute", () => {
  beforeEach(() => {
    window.history.pushState(null, "", "/");
  });
  afterEach(() => {
    window.history.pushState(null, "", "/");
  });

  it("reads no room code from the landing path", () => {
    const { result } = renderHook(() => useRoute());
    expect(result.current.roomCode).toBeNull();
  });

  it("reads an existing room code out of the URL on mount", () => {
    window.history.pushState(null, "", "/room/ABC123");
    const { result } = renderHook(() => useRoute());
    expect(result.current.roomCode).toBe("ABC123");
  });

  it("goToRoom pushes the URL and updates roomCode", () => {
    const { result } = renderHook(() => useRoute());
    act(() => result.current.goToRoom("XYZ789"));

    expect(result.current.roomCode).toBe("XYZ789");
    expect(window.location.pathname).toBe("/room/XYZ789");
  });

  it("updates roomCode when the user navigates back (popstate)", () => {
    const { result } = renderHook(() => useRoute());
    act(() => result.current.goToRoom("AAA111"));
    expect(result.current.roomCode).toBe("AAA111");

    act(() => {
      window.history.pushState(null, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(result.current.roomCode).toBeNull();
  });
});
