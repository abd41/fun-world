/**
 * The one screen in vertical 001: every title's name, from `GET /api/titles`.
 *
 * T014 is the happy path. T015 is everything else, and the point of T015 is
 * that "everything else" is not one thing — the messages below are worded so
 * that whoever is holding the phone can tell WHICH thing went wrong, because
 * each has a different fix:
 *
 *   empty            nothing to do, the catalog really is empty
 *   off-home-network change Wi-Fi
 *   server-unreachable start the server on the laptop
 *   server-error     the server is up and unhappy; look at its log
 *   no-api-url       the app was started without FW_HOST; run ./scripts/setup
 *
 * Styling is deliberately absent (spec 001, Assumptions: "No styling"). The
 * only style rules here are spacing, and there is not a single colour: §14
 * makes `packages/tokens` the sole source of those and it is still empty.
 */
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Button, ScrollView, StyleSheet, Text, View } from "react-native";

import { MISSING_BASE_URL_MESSAGE, apiBaseUrl } from "../api/config";
import { loadCatalog, type CatalogState } from "../api/titles";
import { probeConnection } from "../net/connection";

type ScreenState = { kind: "loading" } | { kind: "no-api-url" } | CatalogState;

export default function CatalogScreen() {
  const [state, setState] = useState<ScreenState>({ kind: "loading" });
  const baseUrl = apiBaseUrl();

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    if (!baseUrl) {
      setState({ kind: "no-api-url" });
      return;
    }
    setState(await loadCatalog({ baseUrl, probeConnection }));
  }, [baseUrl]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Body state={state} baseUrl={baseUrl} />
      {state.kind === "loading" ? null : (
        <View style={styles.action}>
          <Button title="Try again" onPress={() => void load()} />
        </View>
      )}
    </ScrollView>
  );
}

function Body({ state, baseUrl }: { state: ScreenState; baseUrl: string | null }) {
  switch (state.kind) {
    case "loading":
      return (
        <View style={styles.block} testID="state-loading">
          <ActivityIndicator />
          <Text>Checking the catalog…</Text>
        </View>
      );

    case "titles":
      return (
        <View style={styles.block} testID="state-titles">
          {state.titles.map((title) => (
            <Text key={title.id} style={styles.titleName}>
              {title.name}
            </Text>
          ))}
        </View>
      );

    // 200 with an empty array. A success, and it must never read like a
    // failure — FR-008 exists because a viewer who cannot tell these apart
    // goes looking for a broken server that is running perfectly.
    case "empty":
      return (
        <View style={styles.block} testID="state-empty">
          <Text style={styles.headline}>No titles yet</Text>
          <Text>
            The catalog is empty. Nothing is broken — add a title in the Django
            admin, then press Try again.
          </Text>
        </View>
      );

    // Fetch never got an answer, and the handset reports it is not on Wi-Fi.
    // Kept separate from the message below on purpose: the fix is to change
    // network, not to touch the server.
    case "off-home-network":
      return (
        <View style={styles.block} testID="state-off-home-network">
          <Text style={styles.headline}>This phone is not on the home network</Text>
          <Text>
            Fun World runs on one laptop in the house and is not on the public
            internet, so mobile data cannot reach it. Join the home Wi-Fi, then
            press Try again.
          </Text>
        </View>
      );

    // Fetch never got an answer, but the handset believes it is on Wi-Fi, so
    // the likely cause is at the other end.
    case "server-unreachable":
      return (
        <View style={styles.block} testID="state-server-unreachable">
          <Text style={styles.headline}>Cannot reach the Fun World server</Text>
          <Text>
            This phone is on Wi-Fi, but nothing answered. Check the laptop is
            awake and the server is running, then press Try again.
          </Text>
          <Text>Tried: {baseUrl}</Text>
          <Text>{state.detail}</Text>
        </View>
      );

    case "server-error":
      return (
        <View style={styles.block} testID="state-server-error">
          <Text style={styles.headline}>The server answered with an error</Text>
          <Text>
            It is reachable, so this is not a network problem. HTTP {state.status} —
            the server&apos;s own log will say why.
          </Text>
          <Text>Tried: {baseUrl}</Text>
        </View>
      );

    case "no-api-url":
      return (
        <View style={styles.block} testID="state-no-api-url">
          <Text style={styles.headline}>No API address configured</Text>
          <Text>{MISSING_BASE_URL_MESSAGE}</Text>
        </View>
      );
  }
}

const styles = StyleSheet.create({
  page: { padding: 24, gap: 24 },
  block: { gap: 12 },
  action: { alignItems: "flex-start" },
  headline: { fontWeight: "600" },
  titleName: { fontSize: 18 },
});
