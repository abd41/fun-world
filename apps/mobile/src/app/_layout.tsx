/**
 * Root Expo Router layout: one stack, one screen.
 *
 * Vertical 001 is a walking skeleton, so there is nothing to navigate to yet.
 * The stack is here because it gives the screen a header — which keeps the
 * content clear of the status bar without any styling, and styling belongs to
 * vertical 002.
 *
 * No theme, no colours: constitution §14 makes `packages/tokens` the only
 * source of colour, and it has nothing in it yet.
 */
import { Stack } from "expo-router";

export default function RootLayout() {
  return <Stack screenOptions={{ title: "Fun World" }} />;
}
